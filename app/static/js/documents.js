/*
  DocuMind AI frontend script.

  Phase 2: upload, list, and delete documents via /api/documents.
  Phase 3: request text extraction and preview raw extracted text.
  Phase 4: request text cleaning and compare raw vs cleaned text.

  This file does NOT extract or clean text itself - it only calls
  the API and renders whatever the backend returns.
*/

const DOCUMENTS_API = "/api/documents";

document.addEventListener("DOMContentLoaded", () => {
  initUpload();
  initTextPreview();
  loadDocuments();
});

/* ---------------- Upload: button, file picker, drag & drop ---------------- */

function initUpload() {
  const fileInput = document.getElementById("fileInput");
  const dropZone = document.getElementById("dropZone");
  const uploadTriggerBtn = document.getElementById("uploadTriggerBtn");

  uploadTriggerBtn.addEventListener("click", () => fileInput.click());

  const attachTriggerBtn = document.getElementById("attachTriggerBtn");
  if (attachTriggerBtn) attachTriggerBtn.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", () => {
    handleFiles(fileInput.files);
    fileInput.value = ""; // allow re-selecting the same file later
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("drag-active");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("drag-active");
    });
  });

  dropZone.addEventListener("drop", (event) => {
    handleFiles(event.dataTransfer.files);
  });
}

async function handleFiles(fileList) {
  for (const file of Array.from(fileList)) {
    await uploadOneFile(file);
  }
  loadDocuments();
}

async function uploadOneFile(file) {
  const placeholderId = `pending-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  showPendingItem(placeholderId, file.name);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${DOCUMENTS_API}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || "Upload failed.");
    }
  } catch (error) {
    markPendingItemFailed(placeholderId, error.message);
  }
}

/* ---------------- Rendering the document list ---------------- */

function showPendingItem(id, filename) {
  const docList = document.getElementById("docList");
  const item = document.createElement("div");
  item.className = "doc-item";
  item.id = id;
  item.innerHTML = `
    <div class="doc-item-top">
      <i class="bi bi-hourglass-split doc-item-icon"></i>
      <div class="doc-item-info">
        <p class="doc-item-name">${escapeHtml(filename)}</p>
      </div>
    </div>
    <div class="doc-item-meta">
      <span class="badge-muted">Uploading...</span>
    </div>
  `;
  docList.prepend(item);
}

function markPendingItemFailed(id, message) {
  const item = document.getElementById(id);
  if (!item) return;
  item.querySelector(".doc-item-icon").className = "bi bi-exclamation-triangle doc-item-icon doc-item-error";
  item.querySelector(".badge-muted").textContent = message || "Upload failed";
}

async function loadDocuments() {
  const docList = document.getElementById("docList");

  try {
    const response = await fetch(`${DOCUMENTS_API}/`);
    if (!response.ok) throw new Error("Could not load documents.");
    const documents = await response.json();
    renderDocumentList(documents);
  } catch (error) {
    docList.innerHTML = `
      <div class="doc-empty-state">
        <i class="bi bi-exclamation-triangle"></i>
        <p class="doc-empty-title">Could not load documents</p>
        <p class="doc-empty-subtitle">Check that the server is running.</p>
      </div>`;
  }
}

function renderDocumentList(documents) {
  const docList = document.getElementById("docList");

  if (!documents || documents.length === 0) {
    docList.innerHTML = `
      <div class="doc-empty-state">
        <i class="bi bi-inbox"></i>
        <p class="doc-empty-title">No documents yet</p>
        <p class="doc-empty-subtitle">Upload a PDF, DOCX, or TXT file to get started.</p>
      </div>`;
    return;
  }

  docList.innerHTML = documents.map(renderDocumentItem).join("");

  docList.querySelectorAll("[data-delete-id]").forEach((button) => {
    button.addEventListener("click", () => deleteDocument(button.dataset.deleteId));
  });

  docList.querySelectorAll(".extract-btn").forEach((button) => {
    button.addEventListener("click", () => handleExtractButtonClick(button));
  });

  docList.querySelectorAll(".clean-btn").forEach((button) => {
    button.addEventListener("click", () => handleCleanButtonClick(button));
  });
}

function extractionButtonLabel(status) {
  if (status === "extracting") return "Extracting...";
  if (status === "extracted") return "View Text";
  if (status === "extraction_failed") return "Extraction Failed";
  return "Extract Text";
}

function cleaningButtonLabel(status) {
  if (status === "cleaning") return "Cleaning...";
  if (status === "cleaned") return "View Clean Text";
  if (status === "cleaning_failed") return "Cleaning Failed";
  return "Clean Text";
}

function renderDocumentItem(doc) {
  const extractionStatus = doc.extraction_status || "uploaded";
  const cleaningStatus = doc.cleaning_status || "";

  const extractLabel = extractionButtonLabel(extractionStatus);
  const extractDisabled = extractionStatus === "extracting" ? "disabled" : "";

  // The Clean Text button only appears once extraction has succeeded.
  const showCleanBtn = extractionStatus === "extracted";
  const cleanLabel = cleaningButtonLabel(cleaningStatus);
  const cleanDisabled = cleaningStatus === "cleaning" ? "disabled" : "";

  const cleanButtonHtml = showCleanBtn
    ? `<button
        class="clean-btn status-${cleaningStatus || "none"}"
        data-id="${doc.document_id}"
        data-status="${cleaningStatus}"
        data-filename="${escapeHtml(doc.original_filename)}"
        ${cleanDisabled}
      >${cleanLabel}</button>`
    : "";

  return `
    <div class="doc-item">
      <div class="doc-item-top">
        <i class="bi ${extensionIcon(doc.extension)} doc-item-icon"></i>
        <div class="doc-item-info">
          <p class="doc-item-name" title="${escapeHtml(doc.original_filename)}">${escapeHtml(doc.original_filename)}</p>
        </div>
        <button class="icon-btn doc-item-remove" data-delete-id="${doc.document_id}" aria-label="Remove document">
          <i class="bi bi-trash3"></i>
        </button>
      </div>
      <div class="doc-item-meta">
        <span class="badge-muted">${formatFileSize(doc.size_bytes)} · ${formatDate(doc.uploaded_at)}</span>
      </div>
      <div class="doc-item-actions">
        <button
          class="extract-btn status-${extractionStatus}"
          data-id="${doc.document_id}"
          data-status="${extractionStatus}"
          data-filename="${escapeHtml(doc.original_filename)}"
          ${extractDisabled}
        >${extractLabel}</button>
        ${cleanButtonHtml}
      </div>
    </div>`;
}

async function handleExtractButtonClick(button) {
  const documentId = button.dataset.id;
  const status = button.dataset.status;

  if (status === "extracted") {
    openTextPreview(documentId, button.dataset.filename);
    return;
  }

  // "uploaded" or "extraction_failed" -> (re)try extraction
  button.disabled = true;
  button.textContent = extractionButtonLabel("extracting");
  button.className = "extract-btn status-extracting";

  try {
    const response = await fetch(`${DOCUMENTS_API}/${documentId}/extract`, { method: "POST" });
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || "Extraction failed.");
    }
  } catch (error) {
    // The backend already recorded extraction_failed in metadata either way -
    // reloading the list will show the correct state and label.
  }

  loadDocuments();
}

async function handleCleanButtonClick(button) {
  const documentId = button.dataset.id;
  const status = button.dataset.status;

  if (status === "cleaned") {
    openTextPreview(documentId, button.dataset.filename);
    return;
  }

  // no status yet, or "cleaning_failed" -> (re)try cleaning
  button.disabled = true;
  button.textContent = cleaningButtonLabel("cleaning");
  button.className = "clean-btn status-cleaning";

  try {
    const response = await fetch(`${DOCUMENTS_API}/${documentId}/clean`, { method: "POST" });
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || "Cleaning failed.");
    }
  } catch (error) {
    // The backend already recorded cleaning_failed in metadata either way -
    // reloading the list will show the correct state and label.
  }

  loadDocuments();
}

async function deleteDocument(documentId) {
  try {
    const response = await fetch(`${DOCUMENTS_API}/${documentId}`, { method: "DELETE" });
    if (!response.ok) throw new Error("Delete failed.");
    loadDocuments();
  } catch (error) {
    alert("Could not delete the document. Please try again.");
  }
}

/* ---------------- Raw / cleaned text preview modal ---------------- */

let previewRawData = null;
let previewCleanedData = null;

function initTextPreview() {
  const overlay = document.getElementById("textPreviewOverlay");
  const closeBtn = document.getElementById("textPreviewClose");
  const tabs = document.getElementById("textPreviewTabs");

  closeBtn.addEventListener("click", closeTextPreview);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closeTextPreview();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeTextPreview();
  });

  tabs.querySelectorAll(".text-preview-tab").forEach((tab) => {
    tab.addEventListener("click", () => switchPreviewTab(tab.dataset.tab));
  });
}

function closeTextPreview() {
  document.getElementById("textPreviewOverlay").classList.remove("show");
  previewRawData = null;
  previewCleanedData = null;
}

async function openTextPreview(documentId, filename) {
  const overlay = document.getElementById("textPreviewOverlay");
  const title = document.getElementById("textPreviewTitle");
  const subtitle = document.getElementById("textPreviewSubtitle");
  const stats = document.getElementById("textPreviewStats");
  const tabs = document.getElementById("textPreviewTabs");
  const body = document.getElementById("textPreviewBody");

  title.textContent = filename || "Extracted Text";
  subtitle.textContent = "Loading...";
  stats.classList.remove("show");
  tabs.classList.remove("show");
  body.innerHTML = "";
  overlay.classList.add("show");

  previewRawData = null;
  previewCleanedData = null;

  try {
    const rawResponse = await fetch(`${DOCUMENTS_API}/${documentId}/text`);
    if (!rawResponse.ok) throw new Error("Could not load extracted text.");
    previewRawData = await rawResponse.json();
  } catch (error) {
    subtitle.textContent = "";
    body.innerHTML = `<p class="text-preview-page-body">${escapeHtml(error.message)}</p>`;
    return;
  }

  // Cleaned text may or may not exist yet - that's fine, it's optional.
  try {
    const cleanedResponse = await fetch(`${DOCUMENTS_API}/${documentId}/cleaned-text`);
    if (cleanedResponse.ok) {
      previewCleanedData = await cleanedResponse.json();
    }
  } catch (error) {
    previewCleanedData = null;
  }

  if (previewCleanedData) {
    tabs.classList.add("show");
    renderPreviewStats();
    switchPreviewTab("cleaned");
  } else {
    switchPreviewTab("raw");
  }
}

function renderPreviewStats() {
  const stats = document.getElementById("textPreviewStats");
  if (!previewRawData || !previewCleanedData) {
    stats.classList.remove("show");
    return;
  }

  const originalChars = previewRawData.character_count ?? 0;
  const originalWords = previewRawData.text ? previewRawData.text.split(/\s+/).filter(Boolean).length : 0;
  const cleanedChars = previewCleanedData.character_count ?? 0;
  const cleanedWords = previewCleanedData.word_count ?? 0;
  const pageCount = previewRawData.page_count;

  stats.innerHTML = `
    <span>Original: <strong>${originalChars}</strong> chars, <strong>${originalWords}</strong> words</span>
    <span>Cleaned: <strong>${cleanedChars}</strong> chars, <strong>${cleanedWords}</strong> words</span>
    ${pageCount != null ? `<span><strong>${pageCount}</strong> page${pageCount === 1 ? "" : "s"}</span>` : ""}
  `;
  stats.classList.add("show");
}

function switchPreviewTab(tabName) {
  const tabs = document.getElementById("textPreviewTabs");
  const subtitle = document.getElementById("textPreviewSubtitle");

  tabs.querySelectorAll(".text-preview-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });

  const data = tabName === "cleaned" ? previewCleanedData : previewRawData;
  if (!data) return;

  const charCount = data.character_count != null ? `${data.character_count} characters` : "";
  const pageInfo = data.page_count != null ? ` · ${data.page_count} page${data.page_count === 1 ? "" : "s"}` : "";
  const label = tabName === "cleaned" ? "Cleaned text" : "Raw extracted text";
  subtitle.textContent = `${label}${charCount ? " · " + charCount : ""}${pageInfo}`;

  renderTextPreviewBody(data);
}

function renderTextPreviewBody(data) {
  const body = document.getElementById("textPreviewBody");

  if (data.pages && data.pages.length > 0) {
    body.innerHTML = data.pages
      .map(
        (page) => `
        <div class="text-preview-page">
          <span class="text-preview-page-label">Page ${page.page_number}</span>
          <p class="text-preview-page-body">${escapeHtml(page.text) || "(no text on this page)"}</p>
        </div>`
      )
      .join("");
    return;
  }

  body.innerHTML = `<p class="text-preview-page-body">${escapeHtml(data.text)}</p>`;
}

/* ---------------- Small helpers ---------------- */

function extensionIcon(extension) {
  if (extension === ".pdf") return "bi-file-earmark-pdf";
  if (extension === ".docx") return "bi-file-earmark-word";
  if (extension === ".txt") return "bi-file-earmark-text";
  return "bi-file-earmark";
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : text;
  return div.innerHTML;
}