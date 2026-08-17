/*
  DocuMind AI - Phase 2 frontend script.

  Talks to the document API (/api/documents) to upload, list, and
  delete documents. It does NOT read or process file contents -
  that belongs to a later phase. This file only manages the
  upload -> store -> list -> delete flow in the UI.
*/

const DOCUMENTS_API = "/api/documents";

document.addEventListener("DOMContentLoaded", () => {
  initUpload();
  loadDocuments();
});

/* ---------------- Upload: button, file picker, drag & drop ---------------- */

function initUpload() {
  const fileInput = document.getElementById("fileInput");
  const dropZone = document.getElementById("dropZone");
  const uploadTriggerBtn = document.getElementById("uploadTriggerBtn");

  uploadTriggerBtn.addEventListener("click", () => fileInput.click());
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

/* ---------------- Rendering ---------------- */

function showPendingItem(id, filename) {
  const docList = document.getElementById("docList");
  const item = document.createElement("div");
  item.className = "doc-item";
  item.id = id;
  item.innerHTML = `
    <i class="bi bi-hourglass-split doc-item-icon"></i>
    <div class="doc-item-info">
      <p class="doc-item-name">${escapeHtml(filename)}</p>
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
}

function renderDocumentItem(doc) {
  return `
    <div class="doc-item">
      <i class="bi ${extensionIcon(doc.extension)} doc-item-icon"></i>
      <div class="doc-item-info">
        <p class="doc-item-name">${escapeHtml(doc.original_filename)}</p>
        <span class="badge-muted">${formatFileSize(doc.size_bytes)} · ${formatDate(doc.uploaded_at)} · ${escapeHtml(doc.status)}</span>
      </div>
      <button class="icon-btn doc-item-remove" data-delete-id="${doc.document_id}" aria-label="Remove document">
        <i class="bi bi-trash3"></i>
      </button>
    </div>`;
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
  div.textContent = text;
  return div.innerHTML;
}