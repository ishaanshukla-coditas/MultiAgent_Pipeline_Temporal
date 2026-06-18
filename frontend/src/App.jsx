import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import PipelineDetail from './pages/PipelineDetail.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/pipelines/:id" element={<PipelineDetail />} />
      </Routes>
    </BrowserRouter>
  )
}
