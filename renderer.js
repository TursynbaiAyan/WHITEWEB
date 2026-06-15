const API_URL = "http://127.0.0.1:5000";

const mainSearchInput = document.getElementById("mainSearchInput");
const mainAnalyzeBtn = document.getElementById("mainAnalyzeBtn");
const workflowState = document.getElementById("workflowState");
const pipelineView = document.getElementById("pipelineView");
const reportView = document.getElementById("reportView");
const sourcesView = document.getElementById("sourcesView");

const toolsModal = document.getElementById("toolsModal");
const aiModal = document.getElementById("aiModal");
const systemModal = document.getElementById("systemModal");
const toolPanel = document.getElementById("toolPanel");

const chatBox = document.getElementById("chatBox");
const aiInput = document.getElementById("aiInput");

/* ==========================================================
   BASIC HELPERS
========================================================== */

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeText(value) {
  if (value === null || value === undefined || value === "") return "Unknown";
  return String(value);
}

function isPhoneLike(value) {
  const clean = String(value || "").replace(/[^\d+]/g, "");
  return clean.length >= 8 && /^[+\d]/.test(clean);
}

function isUrlLike(value) {
  const q = String(value || "").trim();
  return q.startsWith("http://") || q.startsWith("https://");
}

function isDomainLike(value) {
  const clean = String(value || "")
    .trim()
    .toLowerCase()
    .replace("https://", "")
    .replace("http://", "")
    .split("/")[0];

  return /^[a-z0-9.-]+\.[a-z]{2,}$/.test(clean);
}

function normalizePhone(phone) {
  let clean = String(phone || "").replace(/[^\d+]/g, "");

  if (clean.startsWith("8") && clean.length === 11) {
    clean = "+7" + clean.slice(1);
  }

  if (clean.startsWith("7") && clean.length === 11) {
    clean = "+" + clean;
  }

  return clean;
}

function setLoadingState(text) {
  workflowState.textContent = text;
  pipelineView.innerHTML = `
    <div class="loading-card">
      <div class="loader"></div>
      <strong>${escapeHtml(text)}</strong>
      <p>Agents are processing your request...</p>
    </div>
  `;
  reportView.innerHTML = "Generating report...";
  sourcesView.innerHTML = "Collecting public sources...";
}

function openModal(modal) {
  modal.classList.add("active");
}

function closeModal(modal) {
  modal.classList.remove("active");
}

/* ==========================================================
   MAIN ANALYSIS
========================================================== */

async function runMainAnalysis() {
  const query = mainSearchInput.value.trim();

  if (!query) {
    alert("Enter query first.");
    return;
  }

  if (isPhoneLike(query)) {
    openModal(toolsModal);
    openTool("verifiedIdentity");

    setTimeout(() => {
      const phoneInput = document.getElementById("verifiedPhoneInput");
      const purposeInput = document.getElementById("verifiedPurposeInput");
      const consentInput = document.getElementById("verifiedConsentInput");

      if (phoneInput) phoneInput.value = normalizePhone(query);
      if (purposeInput) purposeInput.value = "Educational university presentation with my own consent";
      if (consentInput) consentInput.checked = true;
    }, 80);

    return;
  }

  setLoadingState("Running multi-agent workflow...");

  try {
    const response = await fetch(`${API_URL}/api/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        query,
        purpose: "Educational public-source analysis and browser intelligence demonstration",
        consent: true
      })
    });

    const data = await response.json();

    if (!data.ok) {
      workflowState.textContent = "Failed";
      pipelineView.innerHTML = `<div class="error-box">${escapeHtml(data.message || "Analysis failed.")}</div>`;
      reportView.innerHTML = "No report.";
      sourcesView.innerHTML = "No sources.";
      return;
    }

    renderAnalysisResult(data.result);
    workflowState.textContent = "Analysis completed";

  } catch (e) {
    workflowState.textContent = "Server error";
    pipelineView.innerHTML = `<div class="error-box">Backend connection failed. Make sure Flask is running on ${API_URL}</div>`;
    reportView.innerHTML = "No report.";
    sourcesView.innerHTML = "No sources.";
  }
}

function renderAnalysisResult(result) {
  renderPipeline(result.pipeline || []);
  renderReport(result);
  renderSources(result.sources || []);

  if (result.verified_profile) {
    renderVerifiedProfileInsideReport(result.verified_profile, result.restricted_layer);
  }
}

function renderPipeline(pipeline) {
  if (!pipeline.length) {
    pipelineView.innerHTML = "No pipeline steps.";
    return;
  }

  let html = "";

  pipeline.forEach((step, index) => {
    const status = step.status || "completed";
    let statusClass = "status-ok";

    if (status === "blocked") statusClass = "status-bad";
    if (status === "warning") statusClass = "status-mid";

    html += `
      <div class="pipeline-step">
        <div class="step-index">${String(index + 1).padStart(2, "0")}</div>
        <div class="step-content">
          <h4>${escapeHtml(step.agent || "Agent")}</h4>
          <span class="${statusClass}">${escapeHtml(status.toUpperCase())}</span>
          <p>${escapeHtml(step.summary || "No summary.")}</p>
        </div>
      </div>
    `;
  });

  pipelineView.innerHTML = html;
}

function renderReport(result) {
  const report = result.final_report || {};
  const security = result.security || {};
  const osint = result.osint || {};
  const restricted = result.restricted_layer || {};

  let html = `
    <div class="report-card">
      <div class="badge">FINAL REPORT</div>
      <h3>${escapeHtml(report.report_title || report.title || "BRIGHTLY Intelligence Report")}</h3>
      <p>${escapeHtml(report.executive_summary || report.summary || "No summary.")}</p>
    </div>

    <div class="verdict-grid">
      <div class="verdict-card">
        <span>Query Type</span>
        <strong>${escapeHtml(result.query_type || "Unknown")}</strong>
      </div>
      <div class="verdict-card">
        <span>Risk Score</span>
        <strong>${escapeHtml(security.risk_score ?? "Unknown")}</strong>
      </div>
      <div class="verdict-card">
        <span>Risk Level</span>
        <strong>${escapeHtml(security.risk_level || "Unknown")}</strong>
      </div>
      <div class="verdict-card">
        <span>Legal Status</span>
        <strong>${escapeHtml(report.final_verdict?.legal_status || "Unknown")}</strong>
      </div>
    </div>
  `;

  if (osint.insights && osint.insights.length) {
    html += `
      <div class="report-card">
        <h3>OSINT Insights</h3>
        ${osint.insights.map(item => `<p>• ${escapeHtml(item)}</p>`).join("")}
      </div>
    `;
  }

  if (security.findings && security.findings.length) {
    html += `
      <div class="report-card">
        <h3>Security Findings</h3>
        ${security.findings.map(item => `<p>• ${escapeHtml(item)}</p>`).join("")}
      </div>
    `;
  }

  html += `
    <div class="report-card restricted-card">
      <div class="badge red">RESTRICTED DATA LAYER</div>
      <h3>Protected Categories</h3>
      <p><strong>Owner identity:</strong> ${escapeHtml(restricted.owner_identity || "REDACTED")}</p>
      <p><strong>SIM registration:</strong> ${escapeHtml(restricted.sim_registration || "BLOCKED")}</p>
      <p><strong>IIN:</strong> ${escapeHtml(restricted.iin || "REDACTED")}</p>
      <p><strong>Address:</strong> ${escapeHtml(restricted.address || "BLOCKED")}</p>
      <p><strong>Banking data:</strong> ${escapeHtml(restricted.banking_data || "NOT ACCESSED")}</p>
      <p><strong>Government database:</strong> ${escapeHtml(restricted.government_database || "NOT ACCESSED")}</p>
      <p><strong>Tax database:</strong> ${escapeHtml(restricted.tax_database || "NOT ACCESSED")}</p>
    </div>
  `;

  if (report.sections && report.sections.length) {
    report.sections.forEach(section => {
      html += `
        <div class="report-card">
          <h3>${escapeHtml(section.title)}</h3>
          <p>${escapeHtml(section.content)}</p>
        </div>
      `;
    });
  }

  reportView.innerHTML = html;
}

function renderVerifiedProfileInsideReport(profile, restricted) {
  const sim = profile.sim_layer || {};
  const business = profile.business_layer || {};

  const html = `
    <div class="report-card verified-card">
      <div class="badge green">VERIFIED IDENTITY PROFILE</div>
      <h3>${escapeHtml(profile.full_name)}</h3>

      <p><strong>Phone:</strong> ${escapeHtml(profile.phone)}</p>
      <p><strong>Identity status:</strong> ${escapeHtml(profile.identity_status)}</p>

      <h4>SIM Registration Layer</h4>
      <p><strong>Registered to:</strong> ${escapeHtml(sim.registered_to)}</p>
      <p><strong>Status:</strong> ${escapeHtml(sim.status)}</p>
      <p><strong>Operator:</strong> ${escapeHtml(sim.operator)}</p>
      <p><strong>Country:</strong> ${escapeHtml(sim.country)}</p>

      <h4>Business / Taxpayer Layer</h4>
      <p><strong>Status:</strong> ${escapeHtml(business.status)}</p>
      <p><strong>Name:</strong> ${escapeHtml(business.name)}</p>
      <p><strong>Owner:</strong> ${escapeHtml(business.owner)}</p>
      <p><strong>Activity:</strong> ${escapeHtml(business.activity)}</p>
      <p><strong>Registry status:</strong> ${escapeHtml(business.registry_status)}</p>

      <h4>Protected Restricted Data</h4>
      <p><strong>IIN:</strong> ${escapeHtml(restricted?.iin || "REDACTED")}</p>
      <p><strong>Address:</strong> ${escapeHtml(restricted?.address || "BLOCKED")}</p>

      <p class="legal-note">${escapeHtml(profile.legal_notice)}</p>
    </div>
  `;

  reportView.innerHTML = html + reportView.innerHTML;
}

function renderSources(sources) {
  if (!sources.length) {
    sourcesView.innerHTML = "No public source results returned.";
    return;
  }

  let html = "";

  sources.forEach((src, index) => {
    html += `
      <div class="source-item">
        <div class="badge">${escapeHtml(src.category || "Web")}</div>
        <h4>${index + 1}. ${escapeHtml(src.title || "Untitled")}</h4>
        <p>${escapeHtml(src.snippet || "No snippet available.")}</p>
        <p class="source-domain">${escapeHtml(src.domain || src.source || "Public source")}</p>
        ${src.url ? `<button class="source-open-btn" data-url="${escapeHtml(src.url)}">Open Source</button>` : ""}
      </div>
    `;
  });

  sourcesView.innerHTML = html;

  document.querySelectorAll(".source-open-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const url = btn.dataset.url;
      if (url) window.open(url, "_blank");
    });
  });
}

/* ==========================================================
   TOOLS
========================================================== */

function openTool(toolName) {
  if (toolName === "verifiedIdentity") {
    toolPanel.innerHTML = `
      <strong>Verified Identity Profile</strong>
      <p>
        Consent-based verified profile layer. Shows approved local verified profile records
        and public metadata. Private government, SIM, tax, banking and hidden databases are not accessed.
      </p>

      <label class="tool-label">Phone number</label>
      <input class="tool-input" id="verifiedPhoneInput" placeholder="+77477850528">

      <label class="tool-label">Purpose</label>
      <input class="tool-input" id="verifiedPurposeInput" value="Educational university presentation with my own consent">

      <label class="tool-check">
        <input type="checkbox" id="verifiedConsentInput">
        I confirm this is my own verified profile or I have lawful consent.
      </label>

      <button class="tool-action" onclick="verifiedIdentityProfileTool()">Open Verified Profile</button>
      <div class="tool-result" id="verifiedIdentityResult">Waiting...</div>
    `;
  }

  if (toolName === "publicIntel") {
    toolPanel.innerHTML = `
      <strong>Public Intelligence</strong>
      <p>
        Runs public-source intelligence search using the backend multi-agent OSINT engine.
      </p>

      <label class="tool-label">Query</label>
      <input class="tool-input" id="publicIntelQuery" placeholder="Ayan, email, phone, domain...">

      <label class="tool-label">Search type</label>
      <select class="tool-input" id="publicIntelType">
        <option value="auto">auto</option>
        <option value="name">name</option>
        <option value="phone">phone</option>
        <option value="username">username</option>
        <option value="email">email</option>
        <option value="domain">domain</option>
        <option value="url">url</option>
      </select>

      <label class="tool-label">Purpose</label>
      <input class="tool-input" id="publicIntelPurpose" value="Educational public-source analysis">

      <label class="tool-check">
        <input type="checkbox" id="publicIntelConsent" checked>
        I confirm lawful purpose for this public-source analysis.
      </label>

      <button class="tool-action" onclick="publicIntelTool()">Run Public Intelligence</button>
      <div class="tool-result" id="publicIntelResult">Waiting...</div>
    `;
  }

  if (toolName === "usernameIntel") {
    toolPanel.innerHTML = `
      <strong>Username Intelligence</strong>
      <p>
        Sherlock-based public username footprint check. Results are possible public matches, not verified identity.
      </p>

      <label class="tool-label">Username</label>
      <input class="tool-input" id="usernameIntelInput" placeholder="leaderkazakhstan">

      <label class="tool-label">Purpose</label>
      <input class="tool-input" id="usernameIntelPurpose" value="Educational public username footprint check">

      <label class="tool-check">
        <input type="checkbox" id="usernameIntelConsent" checked>
        I confirm lawful purpose for this public username check.
      </label>

      <button class="tool-action" onclick="usernameIntelTool()">Run Username Intelligence</button>
      <div class="tool-result" id="usernameIntelResult">Waiting...</div>
    `;
  }

  if (toolName === "phoneMetadata") {
    toolPanel.innerHTML = `
      <strong>Phone Metadata</strong>
      <p>Shows only public numbering metadata. No owner, address or private records.</p>

      <label class="tool-label">Phone</label>
      <input class="tool-input" id="phoneMetadataInput" placeholder="+77477850528">

      <button class="tool-action" onclick="phoneMetadataTool()">Check Metadata</button>
      <div class="tool-result" id="phoneMetadataResult">Waiting...</div>
    `;
  }

  if (toolName === "domainSecurity") {
    toolPanel.innerHTML = `
      <strong>Domain Security</strong>
      <p>Runs public-source domain analysis and security context.</p>

      <label class="tool-label">Domain</label>
      <input class="tool-input" id="domainSecurityInput" placeholder="example.com">

      <button class="tool-action" onclick="domainSecurityTool()">Analyze Domain</button>
      <div class="tool-result" id="domainSecurityResult">Waiting...</div>
    `;
  }

  if (toolName === "passwordSafety") {
    toolPanel.innerHTML = `
      <strong>Password Safety</strong>
      <p>Local-only password strength checker. Password is not sent to server.</p>

      <label class="tool-label">Password</label>
      <input class="tool-input" id="passwordSafetyInput" type="password" placeholder="Type password locally">

      <button class="tool-action" onclick="passwordSafetyTool()">Check Strength</button>
      <div class="tool-result" id="passwordSafetyResult">Waiting...</div>
    `;
  }

  if (toolName === "linkExtractor") {
    toolPanel.innerHTML = `
      <strong>Link Extractor</strong>
      <p>Extract links from any suspicious text.</p>

      <textarea class="tool-textarea" id="linkExtractorInput" placeholder="Paste message here..."></textarea>

      <button class="tool-action" onclick="linkExtractorTool()">Extract Links</button>
      <div class="tool-result" id="linkExtractorResult">Waiting...</div>
    `;
  }

  if (toolName === "reportExport") {
    toolPanel.innerHTML = `
      <strong>Report Export</strong>
      <p>Copy current final report as plain text documentation.</p>

      <button class="tool-action" onclick="reportExportTool()">Generate Export</button>
      <div class="tool-result" id="reportExportResult">Waiting...</div>
    `;
  }
}

async function verifiedIdentityProfileTool() {
  const phone = document.getElementById("verifiedPhoneInput").value.trim();
  const purpose = document.getElementById("verifiedPurposeInput").value.trim();
  const consent = document.getElementById("verifiedConsentInput").checked;
  const resultBox = document.getElementById("verifiedIdentityResult");

  if (!phone) {
    resultBox.textContent = "Enter phone number first.";
    return;
  }

  if (!consent || !purpose) {
    resultBox.textContent = "Consent and legal purpose are required.";
    return;
  }

  resultBox.textContent = "Opening consent-based verified identity profile...";

  try {
    const response = await fetch(`${API_URL}/api/identity/verified-profile`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        phone,
        purpose,
        consent
      })
    });

    const data = await response.json();

    if (!data.ok) {
      resultBox.textContent = data.message || "Verified profile lookup failed.";
      return;
    }

    if (!data.found) {
      const r = data.restricted_layer;

      resultBox.textContent =
`BRIGHTLY VERIFIED IDENTITY PROFILE

Phone:
${data.phone}

Status:
No consent-based verified profile found.

Restricted Layer:
Owner identity: ${r.owner_identity}
SIM registration: ${r.sim_registration}
Address: ${r.address}
IIN: ${r.iin}
Banking data: ${r.banking_data}
Government database: ${r.government_database}
Tax database: ${r.tax_database}
Private databases: ${r.private_databases}

Legal Notice:
${data.legal_notice}`;

      return;
    }

    const p = data.profile;
    const sim = p.sim_layer || {};
    const business = p.business_layer || {};
    const r = data.restricted_layer || {};

    resultBox.textContent =
`BRIGHTLY VERIFIED IDENTITY PROFILE

Mode:
${data.mode}

Phone:
${p.phone}

Full name:
${p.full_name}

Identity status:
${p.identity_status}

SIM Registration Layer:
Registered to: ${sim.registered_to}
Status: ${sim.status}
Operator: ${sim.operator}
Country: ${sim.country}

Business / Taxpayer Layer:
Status: ${business.status}
Name: ${business.name}
Owner: ${business.owner}
Activity: ${business.activity}
Registry status: ${business.registry_status}

Restricted Data Layer:
Owner identity: ${r.owner_identity}
SIM registration: ${r.sim_registration}
IIN: ${r.iin}
Address: ${r.address}
Banking data: ${r.banking_data}
Government database: ${r.government_database}
Tax database: ${r.tax_database}
Private databases: ${r.private_databases}

Data Sources:
- ${p.data_sources.join("\n- ")}

Warning:
${data.warning}

Legal Notice:
${p.legal_notice}`;

  } catch (e) {
    resultBox.textContent = "Server connection failed.";
  }
}

async function publicIntelTool() {
  const query = document.getElementById("publicIntelQuery").value.trim();
  const queryType = document.getElementById("publicIntelType").value;
  const purpose = document.getElementById("publicIntelPurpose").value.trim();
  const consent = document.getElementById("publicIntelConsent").checked;
  const resultBox = document.getElementById("publicIntelResult");

  if (!query) {
    resultBox.textContent = "Enter query first.";
    return;
  }

  resultBox.textContent = "Running public-source intelligence...";

  try {
    const response = await fetch(`${API_URL}/api/osint/deep-search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        query,
        query_type: queryType,
        purpose,
        consent
      })
    });

    const data = await response.json();

    if (!data.ok && !data.result) {
      resultBox.textContent = data.message || "Public intelligence failed.";
      return;
    }

    if (data.blocked) {
      resultBox.textContent = data.answer || "Blocked by legal filter.";
      return;
    }

    const result = data.result || {};
    const report = result.report || {};
    const grouped = report.grouped_results || {};

    let text =
`BRIGHTLY PUBLIC INTELLIGENCE

Query: ${safeText(result.query)}
Type: ${safeText(result.query_type)}
Mode: ${safeText(result.mode)}
Found: ${safeText(report.source_count || 0)}

Summary:
${safeText(report.summary)}

Legal Notice:
${safeText(report.legal_notice || result.legal_notice)}

`;

    Object.keys(grouped).forEach(category => {
      const items = grouped[category] || [];
      text += `\n${category} · ${items.length} source(s)\n`;

      items.forEach((item, index) => {
        text += `
${index + 1}. ${safeText(item.title)}
Domain: ${safeText(item.domain)}
Snippet: ${safeText(item.snippet)}
URL: ${safeText(item.url)}
`;
      });
    });

    resultBox.textContent = text;

  } catch (e) {
    resultBox.textContent = "Server connection failed.";
  }
}

async function usernameIntelTool() {
  const username = document.getElementById("usernameIntelInput").value.trim();
  const purpose = document.getElementById("usernameIntelPurpose").value.trim();
  const consent = document.getElementById("usernameIntelConsent").checked;
  const resultBox = document.getElementById("usernameIntelResult");

  if (!username) {
    resultBox.textContent = "Enter username first.";
    return;
  }

  resultBox.textContent = "Running username intelligence. This can take up to 60 seconds...";

  try {
    const response = await fetch(`${API_URL}/api/osint/sherlock`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        username,
        purpose,
        consent
      })
    });

    const data = await response.json();

    if (!data.ok) {
      resultBox.textContent = data.message || data.result?.message || "Sherlock failed.";
      return;
    }

    const result = data.result || {};
    const grouped = result.grouped_results || {};

    let text =
`BRIGHTLY USERNAME INTELLIGENCE

Username: ${safeText(result.username)}
Found: ${safeText(result.found_count)}
Elapsed: ${safeText(result.elapsed_seconds)}s

Legal Notice:
${safeText(result.legal_notice)}

`;

    Object.keys(grouped).forEach(platform => {
      const items = grouped[platform] || [];
      text += `\n${platform} · ${items.length} result(s)\n`;

      items.forEach((item, index) => {
        text += `
${index + 1}. ${safeText(item.url)}
Domain: ${safeText(item.domain)}
Status: ${safeText(item.status)}
Confidence: ${safeText(item.confidence)}
`;
      });
    });

    resultBox.textContent = text;

  } catch (e) {
    resultBox.textContent = "Server connection failed or Sherlock timed out.";
  }
}

async function phoneMetadataTool() {
  const phone = document.getElementById("phoneMetadataInput").value.trim();
  const resultBox = document.getElementById("phoneMetadataResult");

  if (!phone) {
    resultBox.textContent = "Enter phone number.";
    return;
  }

  resultBox.textContent = "Checking phone metadata...";

  try {
    const response = await fetch(`${API_URL}/api/osint/phone`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ phone })
    });

    const data = await response.json();

    if (!data.ok) {
      resultBox.textContent = data.message || "Phone metadata failed.";
      return;
    }

    const meta = data.metadata || data.numbering_metadata || {};

    resultBox.textContent =
`BRIGHTLY PHONE METADATA

Input: ${safeText(data.input || phone)}
International: ${safeText(data.formatted?.international)}
E.164: ${safeText(data.formatted?.e164)}

Country code: +${safeText(meta.country_code)}
Region code: ${safeText(meta.region_code)}
Location: ${safeText(meta.location_en)}
Carrier: ${safeText(meta.carrier_en)}
Timezones: ${(meta.timezones || []).join(", ") || "Unknown"}
Possible: ${safeText(meta.is_possible)}
Valid: ${safeText(meta.is_valid)}

Privacy Notice:
${safeText(data.privacy_notice || "Public metadata only. No owner lookup.")}`;

  } catch (e) {
    resultBox.textContent = "Server connection failed.";
  }
}

async function domainSecurityTool() {
  const domain = document.getElementById("domainSecurityInput").value.trim();
  const resultBox = document.getElementById("domainSecurityResult");

  if (!domain) {
    resultBox.textContent = "Enter domain.";
    return;
  }

  resultBox.textContent = "Running domain analysis...";

  try {
    const response = await fetch(`${API_URL}/api/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        query: domain,
        purpose: "Public domain security analysis",
        consent: true
      })
    });

    const data = await response.json();

    if (!data.ok) {
      resultBox.textContent = data.message || "Domain analysis failed.";
      return;
    }

    const result = data.result;
    const security = result.security || {};

    resultBox.textContent =
`BRIGHTLY DOMAIN SECURITY

Domain:
${domain}

Risk score:
${safeText(security.risk_score)}

Risk level:
${safeText(security.risk_level)}

Findings:
- ${(security.findings || []).join("\n- ")}

Sources found:
${(result.sources || []).length}`;

  } catch (e) {
    resultBox.textContent = "Server connection failed.";
  }
}

function passwordSafetyTool() {
  const password = document.getElementById("passwordSafetyInput").value;
  const resultBox = document.getElementById("passwordSafetyResult");

  if (!password) {
    resultBox.textContent = "Enter password locally.";
    return;
  }

  let score = 0;
  const notes = [];

  if (password.length >= 12) {
    score += 30;
    notes.push("Good length: 12+ characters");
  } else if (password.length >= 8) {
    score += 15;
    notes.push("Acceptable length, but 12+ is better");
  } else {
    notes.push("Too short");
  }

  if (/[A-Z]/.test(password)) {
    score += 15;
    notes.push("Contains uppercase letters");
  } else {
    notes.push("No uppercase letters");
  }

  if (/[a-z]/.test(password)) {
    score += 15;
    notes.push("Contains lowercase letters");
  } else {
    notes.push("No lowercase letters");
  }

  if (/[0-9]/.test(password)) {
    score += 15;
    notes.push("Contains numbers");
  } else {
    notes.push("No numbers");
  }

  if (/[^A-Za-z0-9]/.test(password)) {
    score += 20;
    notes.push("Contains symbols");
  } else {
    notes.push("No symbols");
  }

  const common = ["123456", "password", "qwerty", "admin", "111111", "123456789"];
  if (common.some(x => password.toLowerCase().includes(x))) {
    score -= 35;
    notes.push("Common weak pattern detected");
  }

  score = Math.max(0, Math.min(100, score));

  let level = "Weak";
  if (score >= 75) level = "Strong";
  else if (score >= 45) level = "Medium";

  resultBox.textContent =
`BRIGHTLY PASSWORD SAFETY

Score: ${score}/100
Level: ${level}

Notes:
- ${notes.join("\n- ")}

Privacy:
This check is local only. Password is not sent to the server.`;
}

function linkExtractorTool() {
  const text = document.getElementById("linkExtractorInput").value;
  const resultBox = document.getElementById("linkExtractorResult");

  const links = text.match(/https?:\/\/[^\s]+|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:\/[^\s]*)?/g) || [];

  if (!links.length) {
    resultBox.textContent = "No links found.";
    return;
  }

  resultBox.textContent =
`BRIGHTLY LINK EXTRACTOR

Found ${links.length} link(s):

${links.map((link, i) => `${i + 1}. ${link}`).join("\n")}`;
}

function reportExportTool() {
  const resultBox = document.getElementById("reportExportResult");

  const exportText =
`BRIGHTLY INTELLIGENCE REPORT EXPORT

WORKFLOW:
${pipelineView.innerText}

REPORT:
${reportView.innerText}

SOURCES:
${sourcesView.innerText}`;

  resultBox.textContent = exportText;

  navigator.clipboard?.writeText(exportText).catch(() => {});
}

/* ==========================================================
   AI CHAT
========================================================== */

function addChatMessage(type, text) {
  const div = document.createElement("div");
  div.className = "chat-msg " + type;
  div.innerHTML = `
    <strong>${type === "user" ? "You" : "BRIGHTLY AI"}</strong>
    <p>${escapeHtml(text)}</p>
  `;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendAiMessage() {
  const message = aiInput.value.trim();

  if (!message) return;

  addChatMessage("user", message);
  aiInput.value = "";

  const context =
`Current workflow:
${pipelineView.innerText}

Current report:
${reportView.innerText}

Current sources:
${sourcesView.innerText}`;

  addChatMessage("bot", "Thinking...");

  const lastMsg = chatBox.lastElementChild;

  try {
    const response = await fetch(`${API_URL}/api/ai/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message,
        context
      })
    });

    const data = await response.json();
    lastMsg.remove();

    if (data.ok) {
      addChatMessage("bot", data.answer);
    } else {
      addChatMessage("bot", data.answer || data.message || "AI error.");
    }

  } catch (e) {
    lastMsg.remove();
    addChatMessage("bot", "Backend connection failed.");
  }
}

/* ==========================================================
   API HEALTH
========================================================== */

async function checkHealth() {
  try {
    const response = await fetch(`${API_URL}/api/health`);
    const data = await response.json();

    alert(`BRIGHTLY API: ${data.ok ? "ONLINE" : "OFFLINE"}\nService: ${data.service}\nVersion: ${data.version}`);
  } catch (e) {
    alert("BRIGHTLY API is offline. Run backend/app.py first.");
  }
}

/* ==========================================================
   EVENTS
========================================================== */

mainAnalyzeBtn.addEventListener("click", runMainAnalysis);

mainSearchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runMainAnalysis();
});

document.querySelectorAll(".example-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    mainSearchInput.value = btn.dataset.example;
  });
});

document.getElementById("openToolsBtn").addEventListener("click", () => openModal(toolsModal));
document.getElementById("closeToolsBtn").addEventListener("click", () => closeModal(toolsModal));

document.getElementById("openAiBtn").addEventListener("click", () => openModal(aiModal));
document.getElementById("closeAiBtn").addEventListener("click", () => closeModal(aiModal));

document.getElementById("openSystemBtn").addEventListener("click", () => openModal(systemModal));
document.getElementById("closeSystemBtn").addEventListener("click", () => closeModal(systemModal));

document.getElementById("healthBtn").addEventListener("click", checkHealth);

document.getElementById("sendAiBtn").addEventListener("click", sendAiMessage);

aiInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendAiMessage();
});

document.getElementById("clearBtn").addEventListener("click", () => {
  workflowState.textContent = "Waiting for input";
  pipelineView.innerHTML = "Enter a query to activate the intelligence pipeline.";
  reportView.innerHTML = "No report generated.";
  sourcesView.innerHTML = "No sources yet.";
});

[toolsModal, aiModal, systemModal].forEach(modal => {
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal(modal);
  });
});

/* ==========================================================
   ANIMATED BACKGROUND
========================================================== */

const canvas = document.getElementById("bgCanvas");
const ctx = canvas.getContext("2d");

let cw;
let ch;
let dots = [];

function resizeCanvas() {
  cw = canvas.width = window.innerWidth;
  ch = canvas.height = window.innerHeight;

  const count = window.innerWidth < 800 ? 70 : 130;

  dots = Array.from({ length: count }, () => ({
    x: Math.random() * cw,
    y: Math.random() * ch,
    vx: (Math.random() - 0.5) * 0.45,
    vy: (Math.random() - 0.5) * 0.45,
    r: Math.random() * 2 + 0.8
  }));
}

function animateBackground() {
  ctx.clearRect(0, 0, cw, ch);

  dots.forEach(dot => {
    dot.x += dot.vx;
    dot.y += dot.vy;

    if (dot.x < 0 || dot.x > cw) dot.vx *= -1;
    if (dot.y < 0 || dot.y > ch) dot.vy *= -1;

    ctx.beginPath();
    ctx.arc(dot.x, dot.y, dot.r, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(65,255,179,0.45)";
    ctx.fill();
  });

  for (let i = 0; i < dots.length; i++) {
    for (let j = i + 1; j < dots.length; j++) {
      const dx = dots[i].x - dots[j].x;
      const dy = dots[i].y - dots[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < 125) {
        ctx.beginPath();
        ctx.moveTo(dots[i].x, dots[i].y);
        ctx.lineTo(dots[j].x, dots[j].y);
        ctx.strokeStyle = `rgba(125,183,255,${0.12 - dist / 1250})`;
        ctx.stroke();
      }
    }
  }

  requestAnimationFrame(animateBackground);
}

resizeCanvas();
animateBackground();
window.addEventListener("resize", resizeCanvas);