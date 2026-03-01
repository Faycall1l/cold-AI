import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload && payload.detail;
    if (typeof detail === "string" && detail.trim()) {
      throw new Error(detail);
    }
    if (Array.isArray(detail) && detail.length) {
      throw new Error(detail.map((item) => item?.msg || String(item)).join(" · "));
    }
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

function App() {
  const [activeTab, setActiveTab] = useState("campaigns");
  const [currentUser, setCurrentUser] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [templateEntries, setTemplateEntries] = useState([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState(null);
  const [campaignData, setCampaignData] = useState({ campaign: null, drafts: [] });

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [sendMode, setSendMode] = useState("dry");
  const [scheduleByDraft, setScheduleByDraft] = useState({});
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [draftLimit, setDraftLimit] = useState(100);
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const [selectedDraftId, setSelectedDraftId] = useState(null);
  const [editorSubject, setEditorSubject] = useState("");
  const [editorBody, setEditorBody] = useState("");
  const [personalizeOpener, setPersonalizeOpener] = useState("");
  const [personalizeCTA, setPersonalizeCTA] = useState("");
  const [personalizeResource, setPersonalizeResource] = useState("");

  const [createForm, setCreateForm] = useState({
    name: "",
    purpose: "",
    channel: "email",
    subject_template: "",
    body_template: "",
  });
  const [templateForm, setTemplateForm] = useState({
    title: "",
    category: "script",
    content: "",
  });
  const [editingTemplateId, setEditingTemplateId] = useState(null);

  const selectedCampaign = campaignData.campaign;

  const statusCounts = useMemo(() => {
    const counts = { draft: 0, approved: 0, rejected: 0, sent: 0, failed: 0 };
    for (const draft of campaignData.drafts) {
      counts[draft.status] = (counts[draft.status] || 0) + 1;
    }
    return counts;
  }, [campaignData.drafts]);

  const selectedDraft = useMemo(
    () => campaignData.drafts.find((draft) => draft.id === selectedDraftId) || null,
    [campaignData.drafts, selectedDraftId],
  );

  useEffect(() => {
    bootstrap();
  }, []);

  async function bootstrap() {
    try {
      const me = await api("/api/me");
      if (!me.authenticated) {
        window.location.href = "/";
        return;
      }
      setCurrentUser(me.user || null);
      await loadCampaigns();
      await loadTemplateLibrary();
      await loadDefaultTemplates();
    } catch {
      window.location.href = "/";
    }
  }

  useEffect(() => {
    if (selectedDraft) {
      setEditorSubject(selectedDraft.subject || "");
      setEditorBody(selectedDraft.body || "");
      setPersonalizeOpener("");
      setPersonalizeCTA("");
      setPersonalizeResource("");
    }
  }, [selectedDraftId]);

  async function loadCampaigns() {
    try {
      const data = await api("/api/campaigns");
      setCampaigns(data.campaigns || []);
      setError("");
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  async function loadDefaultTemplates() {
    try {
      const data = await api("/api/templates/defaults");
      setCreateForm((prev) => ({
        ...prev,
        subject_template: data.subject_template || prev.subject_template,
        body_template: data.body_template || prev.body_template,
      }));
    } catch {
      // ignore and keep fallback
    }
  }

  async function loadTemplateLibrary() {
    try {
      const data = await api("/api/template-library");
      setTemplateEntries(data.entries || []);
      setError("");
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  async function openCampaign(campaignId) {
    try {
      setBusy(true);
      const data = await api(`/api/campaigns/${campaignId}`);
      setSelectedCampaignId(campaignId);
      setCampaignData(data);
      setMessage("");
      setError("");
      setSelectedDraftId(null);
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setBusy(false);
    }
  }

  async function approveDraft(draftId) {
    try {
      const scheduledAt = scheduleByDraft[draftId] || "";
      await api(`/api/drafts/${draftId}/approve`, {
        method: "POST",
        body: JSON.stringify({ scheduled_at: scheduledAt }),
      });
      setMessage(`Draft #${draftId} approved.`);
      setError("");
      await openCampaign(selectedCampaignId);
      setSelectedDraftId(draftId);
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  async function rejectDraft(draftId) {
    try {
      await api(`/api/drafts/${draftId}/reject`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setMessage(`Draft #${draftId} rejected.`);
      setError("");
      await openCampaign(selectedCampaignId);
      setSelectedDraftId(draftId);
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  async function saveDraftEdits() {
    if (!selectedDraft) {
      return;
    }
    try {
      await api(`/api/drafts/${selectedDraft.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          subject: editorSubject,
          body: editorBody,
        }),
      });
      setMessage(`Draft #${selectedDraft.id} saved.`);
      setError("");
      await openCampaign(selectedCampaignId);
      setSelectedDraftId(selectedDraft.id);
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  function applyQuickPersonalization() {
    let body = editorBody;

    if (personalizeOpener.trim()) {
      body = `${personalizeOpener.trim()}\n\n${body}`;
    }

    if (personalizeResource.trim()) {
      body = `${body}\n\nUseful link:\n${personalizeResource.trim()}`;
    }

    if (personalizeCTA.trim()) {
      body = `${body}\n\n${personalizeCTA.trim()}`;
    }

    setEditorBody(body.trim());
  }

  async function sendDue() {
    try {
      const dryRun = sendMode === "dry";
      const result = await api(`/api/campaigns/${selectedCampaignId}/send-due`, {
        method: "POST",
        body: JSON.stringify({ dry_run: dryRun }),
      });
      setMessage(`Send complete (${dryRun ? "dry-run" : "real"}): sent=${result.sent}, failed=${result.failed}`);
      setError("");
      await openCampaign(selectedCampaignId);
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  async function generateDraftsForCampaign(campaignId) {
    try {
      const result = await api(`/api/campaigns/${campaignId}/generate-drafts`, {
        method: "POST",
        body: JSON.stringify({ limit: Number(draftLimit) || 100 }),
      });
      setMessage(`Draft generation done: created=${result.created}, ignored=${result.ignored}.`);
      setError("");
      await loadCampaigns();
      await openCampaign(campaignId);
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  async function createCampaign() {
    const payload = {
      name: createForm.name.trim(),
      purpose: createForm.purpose.trim(),
      channel: createForm.channel,
      subject_template: createForm.subject_template,
      body_template: createForm.body_template,
    };

    if (!payload.name || !payload.subject_template.trim() || !payload.body_template.trim()) {
      setError("Name, subject template, and body template are required.");
      return;
    }

    try {
      const result = await api("/api/campaigns", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setShowCreateModal(false);
      setCreateForm((prev) => ({ ...prev, name: "", purpose: "", channel: "email" }));
      setMessage(`Campaign created (#${result.campaign_id}).`);
      setError("");
      await loadCampaigns();
      await openCampaign(result.campaign_id);
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  function goHome() {
    setSelectedCampaignId(null);
    setCampaignData({ campaign: null, drafts: [] });
    setMessage("");
    setError("");
    setSelectedDraftId(null);
    loadCampaigns();
  }

  function switchTab(tabName) {
    setActiveTab(tabName);
    setMessage("");
    setError("");
    if (tabName !== "campaigns") {
      setSelectedCampaignId(null);
      setSelectedDraftId(null);
    }
    if (tabName === "scripts") {
      resetTemplateForm("script");
    }
    if (tabName === "descriptions") {
      resetTemplateForm("product");
    }
  }

  async function logout() {
    await api("/auth/logout", { method: "POST", body: JSON.stringify({}) });
    window.location.href = "/";
  }

  async function changePassword() {
    if (!passwordForm.current_password || !passwordForm.new_password) {
      setError("Current and new password are required.");
      return;
    }
    if (passwordForm.new_password.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setError("Password confirmation does not match.");
      return;
    }

    try {
      await api("/auth/email/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password,
        }),
      });
      setShowPasswordModal(false);
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
      setMessage("Password updated successfully.");
      setError("");
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  function resetTemplateForm(defaultCategory = "script") {
    setTemplateForm({ title: "", category: defaultCategory, content: "" });
    setEditingTemplateId(null);
  }

  async function saveTemplateEntry() {
    if (!templateForm.title.trim() || !templateForm.content.trim()) {
      setError("Template title and content are required.");
      return;
    }

    try {
      const payload = { ...templateForm };
      if (activeTab === "scripts") {
        payload.category = "script";
      }
      if (activeTab === "descriptions" && payload.category === "script") {
        payload.category = "product";
      }

      if (editingTemplateId) {
        await api(`/api/template-library/${editingTemplateId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
        setMessage("Template entry updated.");
      } else {
        await api("/api/template-library", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setMessage("Template entry created.");
      }
      setError("");
      resetTemplateForm(activeTab === "scripts" ? "script" : "product");
      await loadTemplateLibrary();
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  function editTemplateEntry(entry) {
    setTemplateForm({
      title: entry.title || "",
      category: entry.category || "script",
      content: entry.content || "",
    });
    setEditingTemplateId(entry.id);
  }

  async function deleteTemplateEntry(entryId) {
    try {
      await api(`/api/template-library/${entryId}`, { method: "DELETE" });
      setMessage("Template entry deleted.");
      setError("");
      if (editingTemplateId === entryId) {
        resetTemplateForm();
      }
      await loadTemplateLibrary();
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  const scriptEntries = templateEntries.filter((entry) => entry.category === "script");
  const descriptionEntries = templateEntries.filter((entry) => entry.category === "product" || entry.category === "service");

  const headerTitle = activeTab === "scripts"
    ? "Scripts"
    : activeTab === "descriptions"
      ? "Descriptions"
      : activeTab === "settings"
        ? "Settings"
      : (selectedCampaign ? selectedCampaign.name : "Campaigns");
  const headerSubtitle = activeTab === "scripts"
    ? "Store reusable outreach scripts"
    : activeTab === "descriptions"
      ? "Store product and service descriptions"
      : activeTab === "settings"
        ? "Account and workspace preferences"
      : (selectedCampaign && selectedCampaign.purpose
        ? selectedCampaign.purpose
        : "Run outreach workflows with a click-first control panel");

  return React.createElement("div", { className: "container" },
    React.createElement("div", { className: "crumb" }, "cold-ai / workspace"),
    React.createElement("div", { className: "app-shell" },
      React.createElement("aside", { className: "sidebar card" },
        React.createElement("div", { className: "sidebar-main" },
          React.createElement("div", { className: "sidebar-title" }, "Navigation"),
          React.createElement("button", {
            className: `nav-item ${activeTab === "campaigns" ? "active" : ""}`,
            onClick: () => switchTab("campaigns"),
          }, "Campaigns"),
          React.createElement("button", {
            className: `nav-item ${activeTab === "scripts" ? "active" : ""}`,
            onClick: () => switchTab("scripts"),
          }, "Scripts"),
          React.createElement("button", {
            className: `nav-item ${activeTab === "descriptions" ? "active" : ""}`,
            onClick: () => switchTab("descriptions"),
          }, "Descriptions")
          ,
          React.createElement("button", {
            className: `nav-item ${activeTab === "settings" ? "active" : ""}`,
            onClick: () => switchTab("settings"),
          }, "Settings")
        ),
        React.createElement("div", { className: "sidebar-footer" },
          currentUser && currentUser.provider === "email" && React.createElement("button", { className: "btn btn-soft nav-footer-btn", onClick: () => setShowPasswordModal(true) }, "Change Password"),
          React.createElement("button", { className: "btn btn-soft nav-footer-btn", onClick: logout }, "Logout")
        )
      ),

      React.createElement("main", { className: "main-pane" },
        React.createElement("div", { className: "topbar" },
          React.createElement("div", null,
            React.createElement("h1", { className: "title" }, headerTitle),
            React.createElement("div", { className: "subtitle" }, headerSubtitle)
          ),
          React.createElement("div", { className: "row" },
            currentUser && React.createElement("div", { className: "user-chip" }, currentUser.email || currentUser.name || "User"),
            activeTab === "campaigns" && !selectedCampaign && React.createElement("button", { className: "btn btn-dark btn-top", onClick: () => setShowCreateModal(true) }, "Create Campaign"),
            activeTab === "campaigns" && selectedCampaign && React.createElement("button", { className: "btn btn-soft btn-top", onClick: goHome }, "Back")
          )
        ),

        message && React.createElement("div", { className: "message" }, message),
        error && React.createElement("div", { className: "error" }, error),
        busy && React.createElement("div", { className: "muted", style: { marginBottom: "10px" } }, "Loading…"),

        activeTab === "campaigns" && !selectedCampaign && React.createElement(CampaignList, {
          campaigns,
          onOpen: openCampaign,
          draftLimit,
          setDraftLimit,
          onGenerateDrafts: generateDraftsForCampaign,
        }),

        activeTab === "campaigns" && selectedCampaign && React.createElement(CampaignDetails, {
          campaign: selectedCampaign,
          drafts: campaignData.drafts,
          selectedDraftId,
          setSelectedDraftId,
          statusCounts,
          sendMode,
          setSendMode,
          onSendDue: sendDue,
          onGenerateDrafts: generateDraftsForCampaign,
          draftLimit,
          setDraftLimit,
          onApprove: approveDraft,
          onReject: rejectDraft,
          scheduleByDraft,
          setScheduleByDraft,
          editorSubject,
          setEditorSubject,
          editorBody,
          setEditorBody,
          onSaveEdits: saveDraftEdits,
          personalizeOpener,
          setPersonalizeOpener,
          personalizeCTA,
          setPersonalizeCTA,
          personalizeResource,
          setPersonalizeResource,
          onApplyQuickPersonalization: applyQuickPersonalization,
        }),

        activeTab === "scripts" && React.createElement(TemplatesPage, {
          pageType: "scripts",
          entries: scriptEntries,
          form: templateForm,
          setForm: setTemplateForm,
          editingId: editingTemplateId,
          onSave: saveTemplateEntry,
          onCancelEdit: () => resetTemplateForm("script"),
          onEdit: editTemplateEntry,
          onDelete: deleteTemplateEntry,
        }),

        activeTab === "descriptions" && React.createElement(TemplatesPage, {
          pageType: "descriptions",
          entries: descriptionEntries,
          form: templateForm,
          setForm: setTemplateForm,
          editingId: editingTemplateId,
          onSave: saveTemplateEntry,
          onCancelEdit: () => resetTemplateForm("product"),
          onEdit: editTemplateEntry,
          onDelete: deleteTemplateEntry,
        }),

        activeTab === "settings" && React.createElement(SettingsPage, {
          currentUser,
          onOpenPasswordModal: () => setShowPasswordModal(true),
        })
      )
    ),

    showCreateModal && React.createElement(CreateCampaignModal, {
      form: createForm,
      setForm: setCreateForm,
      onClose: () => setShowCreateModal(false),
      onCreate: createCampaign,
    }),

    showPasswordModal && React.createElement(ChangePasswordModal, {
      form: passwordForm,
      setForm: setPasswordForm,
      onClose: () => setShowPasswordModal(false),
      onSubmit: changePassword,
    })
  );
}

function SettingsPage({ currentUser, onOpenPasswordModal }) {
  return React.createElement("div", { className: "card controls-card" },
    React.createElement("div", { className: "field" },
      React.createElement("div", { className: "muted" }, "Signed in as"),
      React.createElement("div", { className: "template-title", style: { marginTop: "6px" } }, currentUser?.email || currentUser?.name || "User")
    ),
    React.createElement("div", { className: "field" },
      React.createElement("div", { className: "muted" }, "Provider"),
      React.createElement("div", { className: "menu-meta", style: { margin: "6px 0 0 0" } }, currentUser?.provider || "unknown")
    ),
    currentUser?.provider === "email" && React.createElement("div", { className: "row", style: { marginTop: "8px" } },
      React.createElement("button", { className: "btn btn-soft", onClick: onOpenPasswordModal }, "Change Password")
    )
  );
}

function TemplatesPage({ pageType, entries, form, setForm, editingId, onSave, onCancelEdit, onEdit, onDelete }) {
  const isScripts = pageType === "scripts";
  const titlePlaceholder = isScripts ? "Dentist follow-up script" : "Service overview";
  const contentPlaceholder = isScripts
    ? "Write the reusable script here..."
    : "Write the reusable product/service description here...";

  return React.createElement(React.Fragment, null,
    React.createElement("div", { className: "card controls-card", style: { marginBottom: "12px" } },
      React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "Title"),
        React.createElement("input", {
          className: "input",
          value: form.title,
          onChange: (event) => setForm((prev) => ({ ...prev, title: event.target.value })),
          placeholder: titlePlaceholder,
        })
      ),
      !isScripts && React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "Category"),
        React.createElement("select", {
          className: "select",
          style: { maxWidth: "240px" },
          value: form.category === "script" ? "product" : form.category,
          onChange: (event) => setForm((prev) => ({ ...prev, category: event.target.value })),
        },
          React.createElement("option", { value: "product" }, "Product Description"),
          React.createElement("option", { value: "service" }, "Service Description")
        )
      ),
      React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "Content"),
        React.createElement("textarea", {
          className: "input",
          rows: 7,
          value: form.content,
          onChange: (event) => setForm((prev) => ({ ...prev, content: event.target.value })),
          placeholder: contentPlaceholder,
        })
      ),
      React.createElement("div", { className: "row" },
        React.createElement("button", { className: "btn btn-dark", onClick: onSave }, editingId ? "Update Entry" : "Add Entry"),
        editingId && React.createElement("button", { className: "btn btn-soft", onClick: onCancelEdit }, "Cancel Edit")
      )
    ),

    !entries.length
      ? React.createElement("div", { className: "card empty" }, isScripts ? "No scripts yet. Add reusable scripts above." : "No descriptions yet. Add product/service descriptions above.")
      : React.createElement("div", { className: "template-grid" },
          entries.map((entry) => React.createElement("div", { key: entry.id, className: "card template-card" },
            React.createElement("div", { className: "template-top" },
              React.createElement("div", { className: "template-title" }, entry.title),
              React.createElement("span", { className: "status" }, entry.category)
            ),
            React.createElement("div", { className: "body-preview" }, entry.content),
            React.createElement("div", { className: "row", style: { marginTop: "10px" } },
              React.createElement("button", { className: "btn btn-soft", onClick: () => onEdit(entry) }, "Edit"),
              React.createElement("button", { className: "btn btn-bad", onClick: () => onDelete(entry.id) }, "Delete")
            )
          ))
        )
  );
}

function CampaignList({ campaigns, onOpen, draftLimit, setDraftLimit, onGenerateDrafts }) {
  return React.createElement(React.Fragment, null,
    React.createElement("div", { className: "card controls-card" },
      React.createElement("div", { className: "row" },
        React.createElement("label", { className: "muted" }, "Draft Limit"),
        React.createElement("input", {
          className: "input",
          style: { maxWidth: "140px" },
          type: "number",
          min: "1",
          max: "5000",
          value: draftLimit,
          onChange: (event) => setDraftLimit(event.target.value),
        }),
        React.createElement("span", { className: "muted" }, "Used by quick Generate Drafts buttons")
      )
    ),

    !campaigns.length
      ? React.createElement("div", { className: "card empty" }, "No campaigns found.")
      : React.createElement("div", { className: "menu-grid" },
          campaigns.map((campaign) => React.createElement(
            "div",
            {
              key: campaign.id,
              className: "menu-card clickable",
              onClick: () => onOpen(campaign.id),
            },
            React.createElement("div", { className: "menu-title" }, campaign.name),
            React.createElement("div", { className: "menu-meta" }, `#${campaign.id} · ${campaign.status} · ${campaign.channel || "email"}`),
            campaign.purpose && React.createElement("div", { className: "menu-meta" }, campaign.purpose),
            React.createElement("div", { className: "menu-actions" },
              React.createElement(
                "button",
                {
                  className: "btn btn-dark",
                  onClick: (event) => {
                    event.stopPropagation();
                    onGenerateDrafts(campaign.id);
                  },
                },
                "Generate Drafts",
              )
            )
          ))
        )
  );
}

function CampaignDetails({
  campaign,
  drafts,
  selectedDraftId,
  setSelectedDraftId,
  statusCounts,
  sendMode,
  setSendMode,
  onSendDue,
  onGenerateDrafts,
  draftLimit,
  setDraftLimit,
  onApprove,
  onReject,
  scheduleByDraft,
  setScheduleByDraft,
  editorSubject,
  setEditorSubject,
  editorBody,
  setEditorBody,
  onSaveEdits,
  personalizeOpener,
  setPersonalizeOpener,
  personalizeCTA,
  setPersonalizeCTA,
  personalizeResource,
  setPersonalizeResource,
  onApplyQuickPersonalization,
}) {
  const [statusFilter, setStatusFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [viewMode, setViewMode] = useState("grid");

  const visibleDrafts = useMemo(() => {
    const lowered = query.trim().toLowerCase();
    return drafts.filter((draft) => {
      const statusOk = statusFilter === "all" || draft.status === statusFilter;
      const text = `${draft.full_name || ""} ${draft.email || ""} ${draft.phone || ""} ${draft.subject || ""} ${draft.specialty || ""} ${draft.city || ""}`.toLowerCase();
      const queryOk = !lowered || text.includes(lowered);
      return statusOk && queryOk;
    });
  }, [drafts, statusFilter, query]);

  const activeDraft = visibleDrafts.find((draft) => draft.id === selectedDraftId)
    || drafts.find((draft) => draft.id === selectedDraftId)
    || null;

  return React.createElement(React.Fragment, null,
    React.createElement("div", { className: "row", style: { marginBottom: "12px" } },
      React.createElement("span", { className: "pill" }, `Draft: ${statusCounts.draft || 0}`),
      React.createElement("span", { className: "pill" }, `Approved: ${statusCounts.approved || 0}`),
      React.createElement("span", { className: "pill" }, `Sent: ${statusCounts.sent || 0}`),
      React.createElement("span", { className: "pill" }, `Failed: ${statusCounts.failed || 0}`),
      React.createElement("span", { className: "pill" }, `Rejected: ${statusCounts.rejected || 0}`),
      React.createElement("span", { className: "pill" }, `Channel: ${campaign.channel || "email"}`)
    ),

    React.createElement("div", { className: "card", style: { padding: "12px", marginBottom: "12px" } },
      React.createElement("div", { className: "row" },
        React.createElement("input", {
          className: "input",
          style: { maxWidth: "130px" },
          type: "number",
          min: "1",
          max: "5000",
          value: draftLimit,
          onChange: (event) => setDraftLimit(event.target.value),
          placeholder: "Draft limit",
        }),
        React.createElement("button", { className: "btn btn-soft", onClick: () => onGenerateDrafts(campaign.id) }, "Generate Drafts"),
        React.createElement("select", {
          className: "select",
          style: { maxWidth: "240px" },
          value: sendMode,
          onChange: (event) => setSendMode(event.target.value),
        },
          React.createElement("option", { value: "dry" }, "Dry-run"),
          React.createElement("option", { value: "real" }, "Real send")
        ),
        React.createElement("button", { className: "btn btn-dark", onClick: onSendDue }, "Send Due")
      )
    ),

    React.createElement("div", { className: "card", style: { padding: "12px", marginBottom: "12px" } },
      React.createElement("div", { className: "row" },
        React.createElement("input", {
          className: "input",
          placeholder: "Search name, email/phone, subject…",
          value: query,
          onChange: (event) => setQuery(event.target.value),
        }),
        React.createElement("select", {
          className: "select",
          style: { maxWidth: "170px" },
          value: statusFilter,
          onChange: (event) => setStatusFilter(event.target.value),
        },
          React.createElement("option", { value: "all" }, "All statuses"),
          React.createElement("option", { value: "draft" }, "Draft"),
          React.createElement("option", { value: "approved" }, "Approved"),
          React.createElement("option", { value: "sent" }, "Sent"),
          React.createElement("option", { value: "failed" }, "Failed"),
          React.createElement("option", { value: "rejected" }, "Rejected")
        ),
        React.createElement("div", { className: "row" },
          React.createElement("button", { className: `btn ${viewMode === "grid" ? "btn-dark" : "btn-soft"}`, onClick: () => setViewMode("grid") }, "Grid"),
          React.createElement("button", { className: `btn ${viewMode === "list" ? "btn-dark" : "btn-soft"}`, onClick: () => setViewMode("list") }, "List"),
          React.createElement("button", { className: `btn ${viewMode === "compact" ? "btn-dark" : "btn-soft"}`, onClick: () => setViewMode("compact") }, "Compact")
        )
      )
    ),

    React.createElement("div", { className: "draft-layout" },
      React.createElement("div", { className: `draft-grid view-${viewMode}` },
        !visibleDrafts.length
          ? React.createElement("div", { className: "card empty" }, "No drafts for this campaign.")
          : visibleDrafts.map((draft) => React.createElement("div", {
              key: draft.id,
              className: `card draft-card clickable ${selectedDraftId === draft.id ? "active" : ""}`,
              onClick: () => setSelectedDraftId(draft.id),
            },
              (() => {
                const recipient = campaign.channel === "whatsapp"
                  ? (draft.phone || draft.email || "-")
                  : (draft.email || draft.phone || "-");
                return React.createElement("div", { className: "draft-top" },
                  React.createElement("div", null,
                    React.createElement("div", { className: "draft-name" }, draft.full_name || "-"),
                    React.createElement("div", { className: "muted" }, recipient),
                    React.createElement("div", { className: "muted" }, `${draft.specialty || "-"} / ${draft.city || "-"}`)
                  ),
                  React.createElement("span", { className: "status" }, draft.status)
                );
              })(),
              React.createElement("div", { className: "draft-label" }, "Subject"),
              React.createElement("div", { className: "draft-subject" }, draft.subject),
              React.createElement("div", { className: "draft-label" }, "Body"),
              React.createElement("div", { className: "body-preview" }, viewMode === "compact" ? `${(draft.body || "").slice(0, 180)}${(draft.body || "").length > 180 ? "…" : ""}` : draft.body)
            ))
      ),

      React.createElement("div", { className: "card editor-card" },
        !activeDraft
          ? React.createElement("div", { className: "empty" }, "Click a draft card to edit and personalize.")
          : React.createElement(React.Fragment, null,
              React.createElement("div", { className: "editor-title" }, `Editing draft #${activeDraft.id}`),
              React.createElement(
                "div",
                { className: "muted", style: { marginBottom: "10px" } },
                `${activeDraft.full_name || "-"} · ${campaign.channel === "whatsapp" ? (activeDraft.phone || activeDraft.email || "-") : (activeDraft.email || activeDraft.phone || "-")}`,
              ),

              React.createElement("div", { className: "field" },
                React.createElement("label", { className: "muted" }, "Subject"),
                React.createElement("textarea", {
                  className: "input",
                  rows: 2,
                  value: editorSubject,
                  onChange: (event) => setEditorSubject(event.target.value),
                })
              ),

              React.createElement("div", { className: "field" },
                React.createElement("label", { className: "muted" }, "Body"),
                React.createElement("textarea", {
                  className: "input",
                  rows: 10,
                  value: editorBody,
                  onChange: (event) => setEditorBody(event.target.value),
                })
              ),

              React.createElement("div", { className: "field" },
                React.createElement("label", { className: "muted" }, "Quick personalization"),
                React.createElement("div", { className: "row" },
                  React.createElement("input", {
                    className: "input",
                    placeholder: "Custom opener (optional)",
                    value: personalizeOpener,
                    onChange: (event) => setPersonalizeOpener(event.target.value),
                  }),
                  React.createElement("input", {
                    className: "input",
                    placeholder: "Resource link (optional)",
                    value: personalizeResource,
                    onChange: (event) => setPersonalizeResource(event.target.value),
                  })
                ),
                React.createElement("input", {
                  className: "input",
                  style: { marginTop: "8px" },
                  placeholder: "CTA line (optional)",
                  value: personalizeCTA,
                  onChange: (event) => setPersonalizeCTA(event.target.value),
                }),
                React.createElement("div", { className: "row", style: { marginTop: "8px" } },
                  React.createElement("button", { className: "btn btn-soft", onClick: onApplyQuickPersonalization }, "Apply Personalization")
                )
              ),

              React.createElement("div", { className: "field" },
                React.createElement("label", { className: "muted" }, "Schedule"),
                React.createElement("input", {
                  className: "input schedule-input",
                  value: scheduleByDraft[activeDraft.id] ?? activeDraft.scheduled_at ?? "",
                  placeholder: "2026-02-28T10:00:00+01:00",
                  onChange: (event) =>
                    setScheduleByDraft((prev) => ({ ...prev, [activeDraft.id]: event.target.value })),
                }),
                React.createElement("div", { className: "schedule-hint" }, "Leave empty to send now (UTC)")
              ),

              React.createElement("div", { className: "row", style: { marginTop: "12px" } },
                React.createElement("button", { className: "btn btn-dark", onClick: onSaveEdits }, "Save Edits"),
                React.createElement("button", { className: "btn btn-ok", onClick: () => onApprove(activeDraft.id) }, "Approve"),
                React.createElement("button", { className: "btn btn-bad", onClick: () => onReject(activeDraft.id) }, "Reject")
              )
            )
      )
    )
  );
}

function CreateCampaignModal({ form, setForm, onClose, onCreate }) {
  return React.createElement("div", { className: "modal-overlay", onClick: onClose },
    React.createElement("div", { className: "modal", onClick: (event) => event.stopPropagation() },
      React.createElement("h3", { className: "modal-title" }, "Create Campaign"),
      React.createElement("div", { className: "muted", style: { marginBottom: "10px" } }, "Build and launch a campaign without leaving the dashboard."),

      React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "Campaign Name"),
        React.createElement("input", {
          className: "input",
          value: form.name,
          onChange: (event) => setForm((prev) => ({ ...prev, name: event.target.value })),
          placeholder: "Algeria Doctors Outreach",
        })
      ),

      React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "Campaign Purpose"),
        React.createElement("textarea", {
          className: "input",
          rows: 2,
          value: form.purpose,
          onChange: (event) => setForm((prev) => ({ ...prev, purpose: event.target.value })),
          placeholder: "Why this campaign exists and what outcome you want",
        })
      ),

      React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "Channel"),
        React.createElement("select", {
          className: "select",
          style: { maxWidth: "220px" },
          value: form.channel || "email",
          onChange: (event) => setForm((prev) => ({ ...prev, channel: event.target.value })),
        },
          React.createElement("option", { value: "email" }, "Email"),
          React.createElement("option", { value: "whatsapp" }, "WhatsApp")
        )
      ),

      React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "Subject Template"),
        React.createElement("textarea", {
          className: "input",
          rows: 3,
          value: form.subject_template,
          onChange: (event) => setForm((prev) => ({ ...prev, subject_template: event.target.value })),
        })
      ),

      React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "Body Template"),
        React.createElement("textarea", {
          className: "input",
          rows: 10,
          value: form.body_template,
          onChange: (event) => setForm((prev) => ({ ...prev, body_template: event.target.value })),
        })
      ),

      React.createElement("div", { className: "row", style: { justifyContent: "flex-end" } },
        React.createElement("button", { className: "btn btn-soft", onClick: onClose }, "Cancel"),
        React.createElement("button", { className: "btn btn-dark", onClick: onCreate }, "Create")
      )
    )
  );
}

function ChangePasswordModal({ form, setForm, onClose, onSubmit }) {
  return React.createElement("div", { className: "modal-overlay", onClick: onClose },
    React.createElement("div", { className: "modal", onClick: (event) => event.stopPropagation() },
      React.createElement("h3", { className: "modal-title" }, "Change Password"),
      React.createElement("div", { className: "muted", style: { marginBottom: "10px" } }, "Update your email account password."),

      React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "Current Password"),
        React.createElement("input", {
          className: "input",
          type: "password",
          value: form.current_password,
          onChange: (event) => setForm((prev) => ({ ...prev, current_password: event.target.value })),
        })
      ),

      React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "New Password"),
        React.createElement("input", {
          className: "input",
          type: "password",
          value: form.new_password,
          onChange: (event) => setForm((prev) => ({ ...prev, new_password: event.target.value })),
        })
      ),

      React.createElement("div", { className: "field" },
        React.createElement("label", { className: "muted" }, "Confirm New Password"),
        React.createElement("input", {
          className: "input",
          type: "password",
          value: form.confirm_password,
          onChange: (event) => setForm((prev) => ({ ...prev, confirm_password: event.target.value })),
        })
      ),

      React.createElement("div", { className: "row", style: { justifyContent: "flex-end" } },
        React.createElement("button", { className: "btn btn-soft", onClick: onClose }, "Cancel"),
        React.createElement("button", { className: "btn btn-dark", onClick: onSubmit }, "Update Password")
      )
    )
  );
}

createRoot(document.getElementById("root")).render(React.createElement(App));
