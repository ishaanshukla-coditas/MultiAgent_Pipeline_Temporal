import axios from 'axios'

export const createPipeline = (topic, simulateWriterFailure = false) =>
  axios.post('/api/pipelines', { topic, simulate_writer_failure: simulateWriterFailure }).then(r => r.data)

export const listPipelines = () =>
  axios.get('/api/pipelines').then(r => r.data)

export const getPipeline = (id) =>
  axios.get(`/api/pipelines/${id}`).then(r => r.data)

export const approvePipeline = (id) =>
  axios.post(`/api/pipelines/${id}/approve`).then(r => r.data)

export const rejectPipeline = (id, feedback) =>
  axios.post(`/api/pipelines/${id}/reject`, { feedback }).then(r => r.data)
