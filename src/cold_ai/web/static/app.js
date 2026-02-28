import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

function App() {
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState(null);
  const [campaignData, setCampaignData] = useState({ campaign: null, drafts: [] });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [sendMode, setSendMode] = useState("dry");
  const [scheduleByDraft, setScheduleByDraft] = useState({});
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [draftLimit, setDraftLimit] = useState(100);
  const [createForm, setCreateForm] = useState({
    name: "",
    subject_template: "",
    body_template: "",
  });

  const selectedCampaign = campaignData.campaign;

  const statusCounts = useMemo(() => {
    const counts = { draft: 0, approved: 0, rejected: 0, sent: 0, failed: 0 };
    for (const draft of campaignData.drafts) {
      counts[draft.status] = (counts[draft.status] || 0) + 1;
    }
    return counts;
  }, [campaignData.drafts]);

  useEffect(() => {
    loadCampaigns();
    loadDefaultTemplates();
  }, []);

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
      // keep empty values as fallback
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
    } catch (err) {
      setError(String(err.message || err));
    }
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
      if (selectedCampaignId === campaignId) {
        await openCampaign(campaignId);
      }
      await loadCampaigns();
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  async function createCampaign() {
    const payload = {
      name: createForm.name.trim(),
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
      setCreateForm((prev) => ({ ...prev, name: "" }));
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
    loadCampaigns();
  }

  return (
    React.createElement("div", { className: "container" },
      React.createElement("div", { className: "crumb" }, "cold-ai / dashboard"),
      React.createElement("div", { className: "topbar" },
        React.createElement("div", null,
          React.createElement("h1", { className: "title" }, selectedCampaign ? selectedCampaign.name : "Campaigns"),
          React.createElement("div", { className: "subtitle" }, "Run outreach workflows with a click-first control panel")
        ),
        React.createElement("div", { className: "row" },
          !selectedCampaign && React.createElement("button", { className: "btn btn-dark", onClick: () => setShowCreateModal(true) }, "Create Campaign"),
          selectedCampaign && React.createElement("button", { className: "btn btn-soft", onClick: goHome }, "Back")
        )
      ),

      message && React.createElement("div", { className: "message" }, message),
      error && React.createElement("div", { className: "error" }, error),
      busy && React.createElement("div", { className: "muted", style: { marginBottom: "10px" } }, "Loading…"),

      !selectedCampaign && React.createElement(CampaignList, {
        campaigns,
        onOpen: openCampaign,
        draftLimit,
        setDraftLimit,
        onGenerateDrafts: generateDraftsForCampaign,
      }),

      selectedCampaign && React.createElement(CampaignDetails, {
        campaign: selectedCampaign,
        drafts: campaignData.drafts,
        statusCounts,
        sendMode,
        setSendMode,
        onSendDue: sendDue,
        onApprove: approveDraft,
        onReject: rejectDraft,
        onGenerateDrafts: generateDraftsForCampaign,
        draftLimit,
        setDraftLimit,
        scheduleByDraft,
        setScheduleByDraft,
      }),

      showCreateModal && React.createElement(CreateCampaignModal, {
        form: createForm,
        setForm: setCreateForm,
        onClose: () => setShowCreateModal(false),
        onCreate: createCampaign,
      })
    )
  );
}

function CampaignList({ campaigns, onOpen, draftLimit, setDraftLimit, onGenerateDrafts }) {
  const content = !campaigns.length
    ? React.createElement("div", { className: "card empty" }, "No campaigns found.")
    : React.createElement("div", { className: "menu-grid" },
        campaigns.map((campaign) => React.createElement("div", { key: campaign.id, className: "menu-card" },
          React.createElement("div", { className: "menu-title" }, campaign.name),
          React.createElement("div", { className: "menu-meta" }, `#${campaign.id} · ${campaign.status}`),
          React.createElement("div", { className: "menu-actions" },
            React.createElement("button", { className: "btn btn-soft", onClick: () => onOpen(campaign.id) }, "Open"),
            React.createElement("button", { className: "btn btn-dark", onClick: () => onGenerateDrafts(campaign.id) }, "Generate Drafts")
          )
        ))
      );

  if (!campaigns.length) {
    return content;
  }

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
    content
  );
}

function CampaignDetails({
  campaign,
  drafts,
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
}) {
  const [statusFilter, setStatusFilter] = useState("all");
  const [query, setQuery] = useState("");

  const visibleDrafts = useMemo(() => {
    const lowered = query.trim().toLowerCase();
    return drafts.filter((draft) => {
      const statusOk = statusFilter === "all" || draft.status === statusFilter;
      const text = `${draft.full_name || ""} ${draft.email || ""} ${draft.subject || ""} ${draft.specialty || ""} ${draft.city || ""}`.toLowerCase();
      const queryOk = !lowered || text.includes(lowered);
      return statusOk && queryOk;
    });
  }, [drafts, statusFilter, query]);

  return React.createElement(React.Fragment, null,
    React.createElement("div", { className: "row", style: { marginBottom: "12px" } },
      React.createElement("span", { className: "pill" }, `Draft: ${statusCounts.draft || 0}`),
      React.createElement("span", { className: "pill" }, `Approved: ${statusCounts.approved || 0}`),
      React.createElement("span", { className: "pill" }, `Sent: ${statusCounts.sent || 0}`),
      React.createElement("span", { className: "pill" }, `Failed: ${statusCounts.failed || 0}`),
      React.createElement("span", { className: "pill" }, `Rejected: ${statusCounts.rejected || 0}`)
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
          React.createElement("option", { value: "real" }, "Real send (SMTP)")
        ),
        React.createElement("button", { className: "btn btn-dark", onClick: onSendDue }, "Send Due")
      )
    ),

    React.createElement("div", { className: "card", style: { padding: "12px", marginBottom: "12px" } },
      React.createElement("div", { className: "row" },
        React.createElement("input", {
          className: "input",
          placeholder: "Search name, email, subject…",
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
        )
      )
    ),

    !visibleDrafts.length
      ? React.createElement("div", { className: "card empty" }, "No drafts for this campaign.")
      : React.createElement("div", { className: "draft-grid" },
          visibleDrafts.map((draft) => React.createElement("div", { key: draft.id, className: "card draft-card" },
            React.createElement("div", { className: "draft-top" },
              React.createElement("div", null,
                React.createElement("div", { className: "draft-name" }, draft.full_name || "-"),
                React.createElement("div", { className: "muted" }, draft.email),
                React.createElement("div", { className: "muted" }, `${draft.specialty || "-"} / ${draft.city || "-"}`)
              ),
              React.createElement("span", { className: "status" }, draft.status)
            ),
            React.createElement("div", { className: "draft-label" }, "Subject"),
            React.createElement("div", { className: "draft-subject" }, draft.subject),
            React.createElement("div", { className: "draft-label" }, "Body"),
            React.createElement("div", { className: "body-preview" }, draft.body),
            React.createElement("div", { className: "draft-label" }, "Schedule"),
            React.createElement("div", { className: "schedule-cell" },
              React.createElement("input", {
                className: "input schedule-input",
                value: scheduleByDraft[draft.id] ?? draft.scheduled_at ?? "",
                placeholder: "2026-02-28T10:00:00+01:00",
                onChange: (event) =>
                  setScheduleByDraft((prev) => ({ ...prev, [draft.id]: event.target.value })),
              }),
              React.createElement("div", { className: "schedule-hint" }, "Leave empty to send now (UTC)")
            ),
            React.createElement("div", { className: "row", style: { marginTop: "10px" } },
              React.createElement("button", { className: "btn btn-ok", onClick: () => onApprove(draft.id) }, "Approve"),
              React.createElement("button", { className: "btn btn-bad", onClick: () => onReject(draft.id) }, "Reject")
            )
          ))
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

createRoot(document.getElementById("root")).render(React.createElement(App));
