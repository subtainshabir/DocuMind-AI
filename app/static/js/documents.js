/*
  DocuMind AI frontend script.

  Phase 2: upload, list, and delete documents via /api/documents.
  Phase 3: request text extraction and preview extracted text via
  /api/documents/{id}/extract and /api/documents/{id}/text.

  This file does NOT extract text itself - it only calls the API
  and renders whatever the backend returns.
*/

const DOCUMENTS_API = "/api/documents";

const EXTRACTION_LABELS = {
  uploaded: "Extract Text",
  extracting: "Extracting...",
  extracted: "View Text",
  extraction_failed: "Extraction Failed",
};

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
}

function renderDocumentItem(doc) {
  const extractionStatus = doc.extraction_status || "uploaded";
  const label = EXTRACTION_LABELS[extractionStatus] || "Extract Text";
  const disabled = extractionStatus === "extracting" ? "disabled" : "";

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
        <button
          class="extract-btn status-${extractionStatus}"
          data-id="${doc.document_id}"
          data-status="${extractionStatus}"
          data-filename="${escapeHtml(doc.original_filename)}"
          ${disabled}
        >${label}</button>
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
  button.textContent = EXTRACTION_LABELS.extracting;
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

async function deleteDocument(documentId) {
  try {
    const response = await fetch(`${DOCUMENTS_API}/${documentId}`, { method: "DELETE" });
    if (!response.ok) throw new Error("Delete failed.");
    loadDocuments();
  } catch (error) {
    alert("Could not delete the document. Please try again.");
  }
}

/* ---------------- Extracted text preview modal ---------------- */

function initTextPreview() {
  const overlay = document.getElementById("textPreviewOverlay");
  const closeBtn = document.getElementById("textPreviewClose");

  closeBtn.addEventListener("click", closeTextPreview);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closeTextPreview();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeTextPreview();
  });
}

function closeTextPreview() {
  document.getElementById("textPreviewOverlay").classList.remove("show");
}

async function openTextPreview(documentId, filename) {
  const overlay = document.getElementById("textPreviewOverlay");
  const title = document.getElementById("textPreviewTitle");
  const subtitle = document.getElementById("textPreviewSubtitle");
  const body = document.getElementById("textPreviewBody");

  title.textContent = filename || "Extracted Text";
  subtitle.textContent = "Loading...";
  body.innerHTML = "";
  overlay.classList.add("show");

  try {
    const response = await fetch(`${DOCUMENTS_API}/${documentId}/text`);
    if (!response.ok) throw new Error("Could not load extracted text.");
    const data = await response.json();
    renderTextPreview(data);
  } catch (error) {
    subtitle.textContent = "";
    body.innerHTML = `<p class="doc-empty-subtitle">${escapeHtml(error.message)}</p>`;
  }
}

function renderTextPreview(data) {
  const subtitle = document.getElementById("textPreviewSubtitle");
  const body = document.getElementById("textPreviewBody");

  const charCount = data.character_count != null ? `${data.character_count} characters` : "";
  const pageInfo = data.page_count != null ? ` · ${data.page_count} page${data.page_count === 1 ? "" : "s"}` : "";
  subtitle.textContent = `Extracted text${charCount ? " · " + charCount : ""}${pageInfo}`;

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