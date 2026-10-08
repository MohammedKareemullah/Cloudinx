import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import { AppProvider } from "./context/AppContext";
import UploadPage from "./pages/UploadPage";
import ConfigurePage from "./pages/ConfigurePage";
import ResultsPage from "./pages/ResultsPage";
import ChatPage from "./pages/ChatPage";

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <div style={{ display: "flex" }}>
          <Sidebar />
          <div style={{ marginLeft: "var(--sidebar-w)", flex: 1, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
            <Topbar />
            <main style={{ flex: 1, padding: "0 32px" }}>
              <Routes>
                <Route path="/" element={<Navigate to="/upload" replace />} />
                <Route path="/upload" element={<UploadPage />} />
                <Route path="/configure" element={<ConfigurePage />} />
                <Route path="/results" element={<ResultsPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="*" element={<Navigate to="/upload" replace />} />
              </Routes>
            </main>
          </div>
        </div>
      </BrowserRouter>
    </AppProvider>
  );
}
