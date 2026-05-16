import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 15000,
});

export async function executeCleaning(datasetId, payload) {
  const response = await api.post(`/datasets/${datasetId}/execute`, payload);
  return response.data;
}

export async function fetchReportHtml(reportName) {
  const response = await api.get(`/datasets/reports/${reportName}`, {
    responseType: "text",
    transformResponse: [(data) => data],
  });
  return response.data;
}

export async function fetchVisualizations(datasetId, inputFilePath) {
  const response = await api.get(`/datasets/${datasetId}/visualizations`, {
    params: { input_file_path: inputFilePath },
  });
  return response.data;
}

export async function uploadDataset(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/datasets/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data; // { dataset_id, file_path, filename }
}

export async function fetchDetect(datasetId, filePath) {
  const response = await api.post(
    `/datasets/${datasetId}/detect`,
    { input_file_path: filePath },
    { timeout: 90000 }, // LLM explanation generation can take 20-30s for large datasets
  );
  return response.data; // { dataset_id, total_issues, total_suggestions, suggestions }
}

