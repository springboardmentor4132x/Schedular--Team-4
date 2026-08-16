import React, { useState, useEffect, useCallback } from "react";
import {
  FiInstagram,
  FiFacebook,
  FiLinkedin,
  FiTwitter,
  FiYoutube,
  FiMusic,
  FiCamera,
  FiMapPin,
  FiAtSign,
  FiPlus,
  FiX,
  FiExternalLink,
  FiCheck,
  FiTrash2,
  FiRefreshCw,
  FiAlertTriangle
} from "react-icons/fi";

import "./SocialAccounts.css";
import { useAuth } from "../../context/AuthContext";
import api from "../../services/api";

const API_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

/*
============================================================
SOCIAL PLATFORMS
============================================================
*/

const PLATFORMS = [
  {
    id: "instagram",
    name: "Instagram",
    description: "Business or Creator Account",
    color: "#E4405F",
    icon: <FiInstagram size={30} />,
  },
  {
    id: "facebook",
    name: "Facebook",
    description: "Pages or Groups",
    color: "#1877F2",
    icon: <FiFacebook size={30} />,
    options: [
      { id: "page", label: "Page" },
      { id: "group", label: "Group" },
    ],
  },
  {
    id: "linkedin",
    name: "LinkedIn",
    description: "Company or Personal Profile",
    color: "#0A66C2",
    icon: <FiLinkedin size={30} />,
    options: [
      { id: "company", label: "Company Page" },
      { id: "personal", label: "Personal Profile" },
    ],
  },
  {
    id: "youtube",
    name: "YouTube",
    description: "YouTube Channel",
    color: "#FF0000",
    icon: <FiYoutube size={30} />,
  },
  {
    id: "twitter",
    name: "X / Twitter",
    description: "Any Account Type",
    color: "#111111",
    icon: <FiTwitter size={30} />,
  },
];

/*
============================================================
GET TEAM ID
============================================================
*/

const getTeamId = () => {
  const possibleKeys = [
    "socialpilot_active_team_id",
    "team_id",
    "teamId",
    "current_team_id",
    "currentTeamId",
    "selectedTeamId",
  ];

  for (const key of possibleKeys) {
    const value = localStorage.getItem(key);

    if (value) {
      return value;
    }
  }

  const possibleObjects = [
    "user",
    "currentUser",
    "authUser",
    "currentTeam",
    "team",
  ];

  for (const key of possibleObjects) {
    try {
      const raw = localStorage.getItem(key);

      if (!raw) continue;

      const parsed = JSON.parse(raw);

      if (parsed?.team_id) {
        return parsed.team_id;
      }

      if (parsed?.teamId) {
        return parsed.teamId;
      }

      if (
        parsed?.id &&
        key.toLowerCase().includes("team")
      ) {
        return parsed.id;
      }

      if (parsed?.team?.id) {
        return parsed.team.id;
      }

      if (parsed?.currentTeam?.id) {
        return parsed.currentTeam.id;
      }
    } catch {
      // Ignore invalid JSON
    }
  }

  return null;
};

/*
============================================================
COMPONENT
============================================================
*/

const SocialAccounts = () => {
  const { user, isAuthenticated } = useAuth();

  const [selectedPlatform, setSelectedPlatform] = useState(null);
  const [liveAccounts, setLiveAccounts] = useState([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [message, setMessage] = useState("");
  const [connecting, setConnecting] = useState(false);

  /*
  ==========================================================
  FETCH CONNECTED ACCOUNTS FROM BACKEND API
  ==========================================================
  */

  const fetchConnectedAccounts = useCallback(async () => {
    setLoadingAccounts(true);
    const teamId = getTeamId();
    try {
      const url = teamId ? `/social/accounts?team_id=${teamId}` : '/social/accounts';
      const response = await api.get(url);
      const data = response.data;
      const accountsList = Array.isArray(data)
        ? data
        : (data?.data?.accounts || data?.accounts || []);
      setLiveAccounts(Array.isArray(accountsList) ? accountsList : []);
    } catch (err) {
      console.error("Failed to fetch live connected accounts", err);
    } finally {
      setLoadingAccounts(false);
    }
  }, []);

  useEffect(() => {
    fetchConnectedAccounts();
  }, [fetchConnectedAccounts]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const connectedPlatform = params.get("connected");
    const oauthError = params.get("error");
    const errorPlatform = params.get("platform");

    // If loaded inside an OAuth popup window, notify opener and close self
    if (window.opener && (connectedPlatform || oauthError)) {
      window.opener.postMessage({
        type: 'oauth-success',
        platform: connectedPlatform || errorPlatform || 'facebook',
        success: !!connectedPlatform,
        error: oauthError || null
      }, '*');
      window.close();
      return;
    }

    if (connectedPlatform) {
      const label = connectedPlatform.charAt(0).toUpperCase() + connectedPlatform.slice(1);
      setMessage(`${label} connected successfully. LinkedIn access tokens typically expire after 60 days; reconnect if publishing fails later.`);
      fetchConnectedAccounts();
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (oauthError) {
      const platformLabel = errorPlatform
        ? `${errorPlatform.charAt(0).toUpperCase()}${errorPlatform.slice(1)}`
        : "Social account";
      setMessage(`${platformLabel} connection failed: ${oauthError}`);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [fetchConnectedAccounts]);

  // Listen to message events from popup window
  useEffect(() => {
    const handleOAuthMessage = (event) => {
      if (event.data && event.data.type === 'oauth-success') {
        const { platform, success, error } = event.data;
        if (success) {
          const label = platform.charAt(0).toUpperCase() + platform.slice(1);
          setMessage(`${label} connected successfully.`);
          fetchConnectedAccounts();
        } else {
          const platformLabel = platform
            ? `${platform.charAt(0).toUpperCase()}${platform.slice(1)}`
            : "Social account";
          setMessage(`${platformLabel} connection failed: ${error}`);
        }
      }
    };

    window.addEventListener('message', handleOAuthMessage);
    return () => {
      window.removeEventListener('message', handleOAuthMessage);
    };
  }, [fetchConnectedAccounts]);

  /*
  ==========================================================
  OPEN CONNECT MODAL
  ==========================================================
  */

  const handleConnect = (platform, option = null) => {
    setMessage("");

    setSelectedPlatform({
      ...platform,
      selectedOption: option,
    });
  };

  /*
  ==========================================================
  START REAL OAUTH FLOW VIA BACKEND
  ==========================================================
  */

  const handleLogin = async () => {
    if (!selectedPlatform) return;

    if (!isAuthenticated || !user) {
      setMessage("You are not authenticated. Please login first.");
      return;
    }

    const platformId = selectedPlatform.id;
    const option = selectedPlatform.selectedOption || null;
    const teamId = getTeamId();

    if (!teamId) {
      setMessage("No active team workspace found. Please select or create a team first.");
      return;
    }

    setConnecting(true);
    setMessage("");

    try {
      let endpoint = `/social/connect/${platformId}`;
      if (platformId === 'facebook') {
        endpoint = `/social/facebook/login`;
      }

      const params = new URLSearchParams();
      params.append("team_id", teamId);
      if (option) params.append("type", option);

      const fullUrl = `${endpoint}?${params.toString()}`;
      const response = await api.get(fullUrl);
      const data = response.data;

      const authUrl = data?.authorization_url || data?.redirect_url || data?.data?.authorization_url || data?.data?.redirect_url;

      if (authUrl) {
        // Open OAuth flow in a centered popup window
        const width = 600;
        const height = 650;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;
        window.open(
          authUrl,
          "oauth-popup",
          `width=${width},height=${height},left=${left},top=${top},status=no,resizable=yes,scrollbars=yes`
        );
        closeModal();
      } else {
        setMessage(`OAuth URL generation succeeded for ${selectedPlatform.name}, but no redirect URL was returned.`);
      }
    } catch (err) {
      console.error("OAuth init error", err);
      const detailMsg = err.response?.data?.detail || err.message || "Failed to initialize OAuth.";
      setMessage(`OAuth Configuration Required: ${detailMsg}`);
    } finally {
      setConnecting(false);
    }
  };

  /*
  ==========================================================
  DISCONNECT REAL ACCOUNT FROM BACKEND
  ==========================================================
  */

  const handleDisconnect = async (accountId) => {
    if (!window.confirm("Are you sure you want to disconnect this social media channel?")) {
      return;
    }

    try {
      await api.delete(`/social/accounts/${accountId}`);
      fetchConnectedAccounts();
    } catch (err) {
      console.error("Failed to disconnect account", err);
      alert("Error disconnecting account: " + (err.response?.data?.detail || err.message));
    }
  };

  /*
  ==========================================================
  CLOSE MODAL
  ==========================================================
  */

  const closeModal = () => {
    setSelectedPlatform(null);
    setMessage("");
  };

  /*
  ==========================================================
  RENDER
  ==========================================================
  */

  return (
    <div className="social-accounts-page">

      {/* HEADER */}

      <div className="social-page-header">
        <div>
          <h1>Connected Social Media Accounts</h1>
          <p>
            Manage official OAuth integrations for <strong>Facebook</strong>, <strong>Instagram</strong>, <strong>LinkedIn</strong>, <strong>YouTube</strong>, and <strong>X / Twitter</strong>.
          </p>
        </div>
      </div>

      {message && (
        <div
          style={{
            marginBottom: "24px",
            padding: "14px 16px",
            borderRadius: "10px",
            background: message.includes("failed") || message.includes("Configuration Required")
              ? "#fff1f2"
              : "#f0fdf4",
            border: message.includes("failed") || message.includes("Configuration Required")
              ? "1px solid #fecdd3"
              : "1px solid #bbf7d0",
            color: message.includes("failed") || message.includes("Configuration Required")
              ? "#9f1239"
              : "#166534",
            fontSize: "14px",
            lineHeight: "1.5",
          }}
        >
          {message}
        </div>
      )}

      {/* LIVE CONNECTED ACCOUNTS SECTION */}
      {liveAccounts.length > 0 && (
        <div style={{ marginBottom: "32px" }}>
          <h2 style={{ fontSize: "20px", marginBottom: "16px", color: "var(--text-primary)", fontWeight: "700" }}>
            Active Channels ({liveAccounts.length})
          </h2>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "20px" }}>
            {liveAccounts.map((acc) => {
              const platformKey = (acc.platform || acc.provider || "").toLowerCase();
              const isExpired = acc.status === "expired";
              const connectionType = platformKey === "facebook" ? "Facebook Page" : (platformKey === "linkedin" ? "LinkedIn Company/Personal" : `${platformKey.charAt(0).toUpperCase() + platformKey.slice(1)} Account`);
              const formattedDate = acc.created_at
                ? new Date(acc.created_at).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric'
                  })
                : 'Aug 15, 2026';

              const platformIconsMap = {
                facebook: <FiFacebook size={18} style={{ color: "#1877F2" }} />,
                instagram: <FiInstagram size={18} style={{ color: "#E4405F" }} />,
                linkedin: <FiLinkedin size={18} style={{ color: "#0A66C2" }} />,
                youtube: <FiYoutube size={18} style={{ color: "#FF0000" }} />,
                twitter: <FiTwitter size={18} style={{ color: "#111111" }} />
              };

              return (
                <div
                  key={acc.id}
                  className={`connected-account-card ${isExpired ? "expired" : "active"}`}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    padding: "20px",
                    borderRadius: "16px",
                    background: "rgba(255, 255, 255, 0.03)",
                    border: isExpired ? "1px solid rgba(239, 68, 68, 0.4)" : "1px solid var(--border-color)",
                    position: "relative",
                    backdropFilter: "blur(10px)",
                    transition: "transform 0.2s, box-shadow 0.2s"
                  }}
                >
                  {/* Top Bar with Platform Name & Icon */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                    <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "6px" }}>
                      {platformIconsMap[platformKey] || <FiExternalLink size={18} />}
                      {platformKey.charAt(0).toUpperCase() + platformKey.slice(1)}
                    </span>
                    <span style={{
                      fontSize: "12px",
                      padding: "4px 8px",
                      borderRadius: "6px",
                      background: "rgba(255, 255, 255, 0.05)",
                      color: "var(--text-muted)",
                      fontWeight: "500"
                    }}>
                      {acc.connection_type ? acc.connection_type.charAt(0).toUpperCase() + acc.connection_type.slice(1) : (platformKey === "facebook" ? "Page" : "Personal")}
                    </span>
                  </div>

                  {/* Profile info */}
                  <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "16px" }}>
                    <img
                      src={acc.avatar_url || `https://api.dicebear.com/7.x/identicon/svg?seed=${platformKey}`}
                      alt={acc.account_name}
                      style={{ width: "50px", height: "50px", borderRadius: "50%", border: "2px solid rgba(255, 255, 255, 0.1)", objectFit: "cover" }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: "700", fontSize: "16px", color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {acc.account_name}
                      </div>
                      <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "2px" }}>
                        {connectionType}
                      </div>
                    </div>
                  </div>

                  {/* Status & Date */}
                  <div style={{ 
                    padding: "12px", 
                    borderRadius: "10px", 
                    background: isExpired ? "rgba(239, 68, 68, 0.06)" : "rgba(16, 185, 129, 0.06)", 
                    marginBottom: "16px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px"
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", fontWeight: "600", color: isExpired ? "var(--error)" : "var(--success)" }}>
                      <span style={{
                        width: "8px",
                        height: "8px",
                        borderRadius: "50%",
                        background: isExpired ? "var(--error)" : "var(--success)",
                        display: "inline-block"
                      }} />
                      {isExpired ? "Needs attention" : "Connected"}
                    </div>
                    {isExpired && (
                      <div style={{ fontSize: "12px", color: "var(--error)", fontWeight: "500" }}>
                        {platformKey === "facebook" ? "Facebook connection needs attention." : "Connection has expired."}
                      </div>
                    )}
                    <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      Connected {formattedDate}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div style={{ display: "flex", gap: "10px", marginTop: "auto" }}>
                    {isExpired ? (
                      <button
                        type="button"
                        onClick={() => {
                          const matchingPlatform = PLATFORMS.find(p => p.id === platformKey);
                          if (matchingPlatform) handleConnect(matchingPlatform);
                        }}
                        style={{
                          flex: 1,
                          padding: "8px 12px",
                          borderRadius: "8px",
                          border: "1px solid var(--error)",
                          background: "var(--error)",
                          color: "#ffffff",
                          cursor: "pointer",
                          fontSize: "13px",
                          fontWeight: "600",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "6px",
                          transition: "background 0.2s"
                        }}
                      >
                        <FiRefreshCw size={14} /> Reconnect {platformKey === "facebook" ? "Facebook" : ""}
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          const matchingPlatform = PLATFORMS.find(p => p.id === platformKey);
                          if (matchingPlatform) handleConnect(matchingPlatform);
                        }}
                        style={{
                          flex: 1,
                          padding: "8px 12px",
                          borderRadius: "8px",
                          border: "1px solid var(--border-color)",
                          background: "transparent",
                          color: "var(--text-secondary)",
                          fontSize: "13px",
                          fontWeight: "600",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "6px"
                        }}
                      >
                        <FiRefreshCw size={14} /> Reconnect
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => handleDisconnect(acc.id)}
                      style={{
                        padding: "8px 12px",
                        borderRadius: "8px",
                        border: "1px solid rgba(239, 68, 68, 0.2)",
                        background: "rgba(239, 68, 68, 0.05)",
                        color: "var(--error)",
                        cursor: "pointer",
                        fontSize: "13px",
                        fontWeight: "600",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px",
                        transition: "background 0.2s, color 0.2s"
                      }}
                      title="Disconnect Account"
                    >
                      <FiTrash2 size={14} /> Disconnect
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* PLATFORM SELECTION GRID */}

      <h2 style={{ fontSize: "20px", marginBottom: "16px", color: "#1e293b", fontWeight: "700" }}>
        Connect New Integration
      </h2>

      <div className="social-grid">
        {PLATFORMS.map((platform) => {
          const connectedAccountsForPlatform = liveAccounts.filter(
            a => (a.platform || a.provider || "").toLowerCase() === platform.id
          );
          const isConnected = connectedAccountsForPlatform.length > 0;

          return (
            <div
              key={platform.id}
              className={`social-card ${isConnected ? "connected" : ""}`}
            >
              <div
                className="platform-icon"
                style={{ color: platform.color }}
              >
                {platform.icon}
              </div>

              <h3>{platform.name}</h3>

              <p className="platform-description">
                {platform.description}
              </p>

              {platform.options ? (
                <div className="platform-options">
                  <span className="choose-label">Choose</span>
                  {platform.options.map((option) => (
                    <button
                      key={option.id}
                      className="option-button"
                      onClick={() => handleConnect(platform, option.id)}
                    >
                      <FiPlus size={13} /> {option.label}
                    </button>
                  ))}
                </div>
              ) : (
                <button
                  className={`connect-button ${isConnected ? "connected-button" : ""}`}
                  onClick={() => handleConnect(platform)}
                >
                  {isConnected ? (
                    <>
                      <FiCheck size={15} /> Connected ({connectedAccountsForPlatform.length})
                    </>
                  ) : (
                    <>
                      <FiPlus size={15} /> Connect
                    </>
                  )}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* OAUTH LOGIN MODAL */}

      {selectedPlatform && (
        <div
          className="connection-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeModal();
          }}
        >
          <div className="connection-modal">
            <button
              className="modal-close"
              onClick={closeModal}
              aria-label="Close"
            >
              <FiX size={22} />
            </button>

            <div
              className="modal-icon"
              style={{ color: selectedPlatform.color }}
            >
              {selectedPlatform.icon}
            </div>

            <h2>Connect {selectedPlatform.name}</h2>

            <p>
              Sign in with your official <strong>{selectedPlatform.name}</strong> credentials via OAuth 2.0 to grant publishing permissions.
            </p>

            {selectedPlatform.selectedOption && (
              <div className="selected-account-type">
                Account type: <strong>{selectedPlatform.selectedOption}</strong>
              </div>
            )}

            <button
              className="modal-connect-button"
              onClick={handleLogin}
              disabled={connecting}
            >
              <FiExternalLink size={17} />
              {connecting ? "Initializing OAuth..." : `Login with ${selectedPlatform.name}`}
            </button>

            {message && (
              <div
                style={{
                  marginTop: "16px",
                  padding: "12px",
                  borderRadius: "8px",
                  background: message.includes("Configuration Required") ? "#fff1f2" : "#f0fdf4",
                  border: message.includes("Configuration Required") ? "1px solid #fecdd3" : "1px solid #bbf7d0",
                  color: message.includes("Configuration Required") ? "#9f1239" : "#166534",
                  fontSize: "13px",
                  lineHeight: "1.4"
                }}
              >
                {message}
              </div>
            )}

            <button
              className="modal-cancel-button"
              onClick={closeModal}
              style={{ marginTop: "16px" }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SocialAccounts;