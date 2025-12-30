import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Queue from './pages/Queue'
import JobDetail from './pages/JobDetail'
import Projects from './pages/Projects'
import Settings from './pages/Settings'
import System from './pages/System'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="queue" element={<Queue />} />
        <Route path="jobs/:id" element={<JobDetail />} />
        <Route path="projects" element={<Projects />} />
        <Route path="settings" element={<Settings />} />
        <Route path="system" element={<System />} />
      </Route>
    </Routes>
  )
}

export default App
