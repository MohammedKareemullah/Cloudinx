import { createContext, useContext, useState, useCallback } from "react";

const AppContext = createContext(null);

const DEFAULT_CONFIG = {
  provider: "aws",
  awsRegion: "us-east-1",
  azureRegion: "eastus",
  scenarios: ["cost", "balanced", "performance"],
  groupName: "",
};

export function AppProvider({ children }) {
  const [file, setFile] = useState(null);
  const [fileMeta, setFileMeta] = useState(null); // { name, size, previewRows }
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [assessment, setAssessment] = useState(null); // full API response from /assess/upload
  const [chatHistory, setChatHistory] = useState([]);
  const [isAssessing, setIsAssessing] = useState(false);
  const [assessError, setAssessError] = useState(null);

  const resetAssessment = useCallback(() => {
    setAssessment(null);
    setAssessError(null);
    setChatHistory([]);
  }, []);

  const resetAll = useCallback(() => {
    setFile(null);
    setFileMeta(null);
    setConfig(DEFAULT_CONFIG);
    resetAssessment();
  }, [resetAssessment]);

  const value = {
    file,
    setFile,
    fileMeta,
    setFileMeta,
    config,
    setConfig,
    assessment,
    setAssessment,
    chatHistory,
    setChatHistory,
    isAssessing,
    setIsAssessing,
    assessError,
    setAssessError,
    resetAssessment,
    resetAll,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
