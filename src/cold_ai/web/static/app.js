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
  const [sendMode, setSendMode] = useState("dry");
  const [scheduleByDraft, setScheduleByDraft] = useState({});

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
  }, []);

  async function loadCampaigns() {
    const data = await api("/api/campaigns");
    setCampaigns(data.campaigns || []);
  }

  async function openCampaign(campaignId) {
    const data = await api(`/api/campaigns/${campaignId}`);
    setSelectedCampaignId(campaignId);
    setCampaignData(data);
    setMessage("");
  }

  async function approveDraft(draftId) {
    const scheduledAt = scheduleByDraft[draftId] || "";
    await api(`/api/drafts/${draftId}/approve`, {
      method: "POST",
      body: JSON.stringify({ scheduled_at: scheduledAt }),
    });
    setMessage(`Draft #${draftId} approved.`);
    await openCampaign(selectedCampaignId);
  }

  async function rejectDraft(draftId) {
    await api(`/api/drafts/${draftId}/reject`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    setMessage(`Draft #${draftId} rejected.`);
    await openCampaign(selectedCampaignId);
  }

  async function sendDue() {
    const dryRun = sendMode === "dry";
    const result = await api(`/api/campaigns/${selectedCampaignId}/send-due`, {
      method: "POST",
      body: JSON.stringify({ dry_run: dryRun }),
    });
    setMessage(`Send complete (${dryRun ? "dry-run" : "real"}): sent=${result.sent}, failed=${result.failed}`);
    await openCampaign(selectedCampaignId);
  }

  function goHome() {
    setSelectedCampaignId(null);
    setCampaignData({ campaign: null, drafts: [] });
    setMessage("");
    loadCampaigns();
  }

  return (
    React.createElement("div", { className: "container" },
      React.createElement("div", { className: "topbar" },
        React.createElement("div", null,
          React.createElement("h1", { className: "title" }, selectedCampaign ? selectedCampaign.name : "Campaigns"),
          React.createElement("div", { className: "subtitle" }, "cold-AI outreach operations dashboard")
        ),
        selectedCampaign && React.createElement("button", { className: "btn btn-soft", onClick: goHome }, "Back")
      ),

      message && React.createElement("div", { className: "message" }, message),

      !selectedCampaign && React.createElement(CampaignList, {
        campaigns,
        onOpen: openCampaign,
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
        scheduleByDraft,
        setScheduleByDraft,
      })
    )
  );
}

function CampaignList({ campaigns, onOpen }) {
  if (!campaigns.length) {
    return React.createElement("div", { className: "card empty" }, "No campaigns found.");
  }

  return React.createElement("div", { className: "card table-wrap" },
    React.createElement("table", null,
      React.createElement("thead", null,
        React.createElement("tr", null,
          React.createElement("th", null, "ID"),
          React.createElement("th", null, "Name"),
          React.createElement("th", null, "Status"),
          React.createElement("th", null, "Created"),
          React.createElement("th", null, "Action")
        )
      ),
      React.createElement("tbody", null,
        campaigns.map((campaign) => React.createElement("tr", { key: campaign.id },
          React.createElement("td", null, `#${campaign.id}`),
          React.createElement("td", null, campaign.name),
          React.createElement("td", null, React.createElement("span", { className: "status" }, campaign.status)),
          React.createElement("td", null, campaign.created_at),
          React.createElement("td", null,
            React.createElement("button", { className: "btn btn-dark", onClick: () => onOpen(campaign.id) }, "Open")
          )
        ))
      )
    )
  );
}

function CampaignDetails({
  campaign,
  drafts,
  statusCounts,
  sendMode,
  setSendMode,
  onSendDue,
  onApprove,
  onReject,
  scheduleByDraft,
  setScheduleByDraft,
}) {
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

    !drafts.length
      ? React.createElement("div", { className: "card empty" }, "No drafts for this campaign.")
      : React.createElement("div", { className: "card table-wrap" },
          React.createElement("table", null,
            React.createElement("thead", null,
              React.createElement("tr", null,
                React.createElement("th", null, "Lead"),
                React.createElement("th", null, "Subject"),
                React.createElement("th", null, "Body"),
                React.createElement("th", null, "Status"),
                React.createElement("th", null, "Schedule"),
                React.createElement("th", null, "Actions")
              )
            ),
            React.createElement("tbody", null,
              drafts.map((draft) => React.createElement("tr", { key: draft.id },
                React.createElement("td", null,
                  React.createElement("div", null, draft.full_name || "-"),
                  React.createElement("div", { className: "muted" }, draft.email),
                  React.createElement("div", { className: "muted" }, `${draft.specialty || "-"} / ${draft.city || "-"}`)
                ),
                React.createElement("td", null, draft.subject),
                React.createElement("td", null,
                  React.createElement("div", { className: "body-preview" }, draft.body)
                ),
                React.createElement("td", null, React.createElement("span", { className: "status" }, draft.status)),
                React.createElement("td", null,
                  React.createElement("input", {
                    className: "input",
                    value: scheduleByDraft[draft.id] ?? draft.scheduled_at ?? "",
                    placeholder: "2026-02-28T10:00:00+01:00",
                    onChange: (event) =>
                      setScheduleByDraft((prev) => ({ ...prev, [draft.id]: event.target.value })),
                  }),
                  React.createElement("div", { className: "muted" }, "Empty = now (UTC)")
                ),
                React.createElement("td", null,
                  React.createElement("div", { className: "row" },
                    React.createElement("button", { className: "btn btn-ok", onClick: () => onApprove(draft.id) }, "Approve"),
                    React.createElement("button", { className: "btn btn-bad", onClick: () => onReject(draft.id) }, "Reject")
                  )
                )
              ))
            )
          )
        )
  );
}

createRoot(document.getElementById("root")).render(React.createElement(App));
