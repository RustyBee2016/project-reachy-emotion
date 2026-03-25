import { HashRouter, Routes, Route, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import HomePage from './pages/HomePage'
import TechnologyPage from './pages/TechnologyPage'
import ArchitecturePage from './pages/ArchitecturePage'
import PrivacySafetyPage from './pages/PrivacySafetyPage'
import UseCasesPage from './pages/UseCasesPage'
import AboutPage from './pages/AboutPage'
import ContactPage from './pages/ContactPage'
import PlatformPage from './pages/PlatformPage'
import CareFlowPage from './pages/CareFlowPage'
import SecureFlowPage from './pages/SecureFlowPage'
import DashboardPage from './pages/DashboardPage'
import GovernancePage from './pages/GovernancePage'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#080818' }}>
      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}

export default function App() {
  return (
    <HashRouter>
      <ScrollToTop />
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/platform" element={<PlatformPage />} />
          <Route path="/careflow" element={<CareFlowPage />} />
          <Route path="/secureflow" element={<SecureFlowPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/governance" element={<GovernancePage />} />
          <Route path="/technology" element={<TechnologyPage />} />
          <Route path="/architecture" element={<ArchitecturePage />} />
          <Route path="/privacy" element={<PrivacySafetyPage />} />
          <Route path="/use-cases" element={<UseCasesPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />
        </Routes>
      </Layout>
    </HashRouter>
  )
}
