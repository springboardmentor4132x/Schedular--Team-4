import React, { useState, useEffect, useCallback, useRef } from "react";
import "./CreatePost.css";
import api from "../../services/api";
import Scheduler from "../Scheduler/Scheduler";
import { 
  FiCheck, FiX, FiClock, FiFileText, FiSend, FiImage, FiGlobe, 
  FiAlertCircle, FiRefreshCw, FiLayers, FiCalendar, FiUploadCloud, 
  FiPlus, FiFolderPlus, FiFacebook, FiLinkedin, FiInstagram 
} from "react-icons/fi";

const TRENDING_HASHTAGS = ["#Marketing", "#SocialMedia", "#ContentCreation", "#AI", "#SaaS", "#Tech", "#Growth"];

const CreatePost = () => {
  // Top Level Navigation Tab: "composer", "calendar", "queue"
  const [activeHubTab, setActiveHubTab] = useState("composer");

  const [postContent, setPostContent] = useState("");
  const [selectedAccountIds, setSelectedAccountIds] = useState([]);
  const [connectedAccounts, setConnectedAccounts] = useState([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [scheduleType, setScheduleType] = useState("now");
  const [scheduleDate, setScheduleDate] = useState("");
  
  // Media upload states
  const [uploadedFiles, setUploadedFiles] = useState([]); // Array of { name, size, type, preview, progress }
  const [isDragOver, setIsDragOver] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  // Preview Platform Tab
  const [previewPlatform, setPreviewPlatform] = useState("facebook");

  // Queue & Status States
  const [nextQueueSlot, setNextQueueSlot] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [publishingStatus, setPublishingStatus] = useState(null); // { postId, status, channels: { [accId]: { name, platform, state, error } } }
  const [showStatusModal, setShowStatusModal] = useState(false);

  const fileInputRef = useRef(null);

  const getTeamId = () => {
    return localStorage.getItem("socialpilot_active_team_id") || "";
  };

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
      setConnectedAccounts(Array.isArray(accountsList) ? accountsList : []);
    } catch (err) {
      console.error("Failed to fetch connected accounts for post composer", err);
    } finally {
      setLoadingAccounts(false);
    }
  }, []);

  const fetchNextQueueSlot = useCallback(async () => {
    const teamId = getTeamId();
    if (!teamId) return;
    try {
      const res = await api.get(`/posts/next-queue-slot?team_id=${teamId}`);
      if (res.data?.success) {
        setNextQueueSlot(res.data.next_slot);
      }
    } catch (err) {
      console.error("Failed to fetch next queue slot", err);
    }
  }, []);

  useEffect(() => {
    fetchConnectedAccounts();
    fetchNextQueueSlot();
  }, [fetchConnectedAccounts, fetchNextQueueSlot]);

  // Account selector helper
  const handleAccountToggle = (accountId) => {
    setSelectedAccountIds((prev) =>
      prev.includes(accountId)
        ? prev.filter((id) => id !== accountId)
        : [...prev, accountId]
    );
  };

  // Local drag & drop / file browse handlers
  const processFiles = async (files) => {
    const maxSizeBytes = 10 * 1024 * 1024; // 10MB
    const validFiles = Array.from(files).filter((file) => {
      if (!file.type.startsWith("image/") && !file.type.startsWith("video/")) {
        alert(`Unsupported file type: ${file.name}. Only images and videos are supported.`);
        return false;
      }
      if (file.size > maxSizeBytes) {
        alert(`File too large: ${file.name}. Max allowed size is 10MB.`);
        return false;
      }
      return true;
    });

    if (validFiles.length === 0) return;

    for (const file of validFiles) {
      const localPreview = URL.createObjectURL(file);
      const newFileObj = {
        name: file.name,
        size: (file.size / (1024 * 1024)).toFixed(2) + " MB",
        type: file.type,
        preview: localPreview,
        progress: 0,
        url: null,
        error: null
      };

      setUploadedFiles((prev) => [...prev, newFileObj]);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("platform", "facebook");

      try {
        const response = await api.post("/posts/upload-media", formData, {
          headers: {
            "Content-Type": "multipart/form-data"
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadedFiles((prev) =>
              prev.map((f) =>
                f.preview === localPreview ? { ...f, progress: Math.min(percentCompleted, 99) } : f
              )
            );
          }
        });

        if (response.data && response.data.media_url) {
          setUploadedFiles((prev) =>
            prev.map((f) =>
              f.preview === localPreview ? { ...f, url: response.data.media_url, progress: 100 } : f
            )
          );
        }
      } catch (err) {
        console.error("Failed to upload file", err);
        const errMsg = err.response?.data?.detail || err.message || "Upload failed";
        setUploadedFiles((prev) =>
          prev.map((f) =>
            f.preview === localPreview ? { ...f, progress: 0, error: errMsg } : f
          )
        );
        alert(`Failed to upload ${file.name}: ${errMsg}`);
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files);
    }
  };

  const handleRemoveFile = (previewUrl) => {
    setUploadedFiles((prev) => prev.filter((f) => f.preview !== previewUrl));
  };

  // Add hashtag helper
  const handleHashtagClick = (tag) => {
    setPostContent((prev) => {
      const trimmed = prev.trim();
      return trimmed ? `${trimmed} ${tag}` : tag;
    });
  };

  const startStatusPolling = (postId, targets) => {
    const initialChannels = {};
    targets.forEach((accId) => {
      const acc = connectedAccounts.find(a => a.id === accId);
      initialChannels[accId] = {
        name: acc?.account_name || "Social Account",
        platform: acc?.platform || "social",
        state: "publishing",
        error: null
      };
    });

    setPublishingStatus({
      postId,
      status: "publishing",
      channels: initialChannels
    });
    setShowStatusModal(true);

    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/posts/${postId}`);
        const postData = res.data;

        const updatedChannels = { ...initialChannels };
        const logs = postData.publishing_logs || [];

        logs.forEach((log) => {
          const acc = connectedAccounts.find(a => a.platform === log.platform && targets.includes(a.id));
          if (acc) {
            updatedChannels[acc.id] = {
              ...updatedChannels[acc.id],
              state: log.status === "published" ? "published" : "failed",
              error: log.error_message
            };
          }
        });

        setPublishingStatus((prev) => ({
          ...prev,
          status: postData.status,
          channels: updatedChannels
        }));

        if (postData.status === "published" || postData.status === "failed" || postData.status === "partially_published") {
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Error polling post status:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (selectedAccountIds.length === 0) {
      alert("Please select at least one connected social account.");
      return;
    }

    // Verify all selected accounts are active/connected
    const disconnectedAccounts = [];
    selectedAccountIds.forEach((id) => {
      const acc = connectedAccounts.find(a => a.id === id);
      const isExpired = acc?.status === "expired" || (acc?.expires_at && new Date(acc.expires_at) < new Date());
      if (isExpired) {
        disconnectedAccounts.push(acc.account_name + ` (${acc.platform})`);
      }
    });

    if (disconnectedAccounts.length > 0) {
      alert(
        `Publishing blocked. The following selected accounts are disconnected or expired:\n- ${disconnectedAccounts.join(
          "\n- "
        )}\n\nPlease reconnect these accounts before publishing.`
      );
      return;
    }

    if (!postContent.trim()) {
      alert("Post content cannot be empty.");
      return;
    }

    if (scheduleType === "schedule" && !scheduleDate) {
      alert("Please select a schedule date and time.");
      return;
    }

    if (uploadedFiles.some((f) => f.progress < 100 && !f.error)) {
      alert("Please wait for all media files to finish uploading before publishing.");
      return;
    }

    setIsSubmitting(true);
    const activeTeamId = getTeamId();

    let targetScheduleType = "scheduled";
    let targetScheduledAt = new Date().toISOString();

    if (scheduleType === "now") {
      targetScheduleType = "now";
    } else if (scheduleType === "queue") {
      targetScheduleType = "scheduled";
      targetScheduledAt = nextQueueSlot ? new Date(nextQueueSlot).toISOString() : new Date().toISOString();
    } else if (scheduleType === "schedule") {
      targetScheduleType = "scheduled";
      targetScheduledAt = new Date(scheduleDate).toISOString();
    }

    // Map media preview files
    const mediaUrlsList = uploadedFiles.map((f) => f.url || f.preview);

    const postPayload = {
      team_id: activeTeamId,
      content_text: postContent,
      platform_targets: selectedAccountIds,
      schedule_type: targetScheduleType,
      scheduled_at: targetScheduledAt,
      media_urls: mediaUrlsList
    };

    try {
      const response = await api.post("/posts", postPayload);
      const newPost = response.data;

      if (scheduleType === "now") {
        startStatusPolling(newPost.id, selectedAccountIds);
      } else {
        alert(
          scheduleType === "queue"
            ? "Post added to publishing queue successfully!"
            : "Post scheduled successfully!"
        );
        // Reset state
        setPostContent("");
        setSelectedAccountIds([]);
        setUploadedFiles([]);
        setScheduleType("now");
        setScheduleDate("");
        fetchNextQueueSlot();
      }
    } catch (error) {
      console.error("Failed to create post:", error);
      const detailMsg = error.response?.data?.detail || error.message || "Error creating post.";
      alert(`Error creating post: ${detailMsg}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetryFailedOnly = async () => {
    if (!publishingStatus?.postId) return;
    setIsSubmitting(true);
    try {
      const res = await api.post(`/posts/${publishingStatus.postId}/retry`);
      startStatusPolling(publishingStatus.postId, selectedAccountIds);
    } catch (err) {
      alert(`Retry failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getPlatformIcon = (platformStr) => {
    const p = (platformStr || "").toLowerCase();
    if (p.includes("facebook")) return <FiFacebook />;
    if (p.includes("instagram")) return <FiInstagram />;
    if (p.includes("linkedin")) return <FiLinkedin />;
    return <FiGlobe />;
  };

  // Previews styling helpers
  const renderPlatformSpecificPreview = () => {
    if (previewPlatform === "facebook") {
      return (
        <div className="preview-feed-card facebook">
          <div className="preview-feed-header">
            <div className="preview-feed-avatar">FB</div>
            <div>
              <div className="preview-feed-author">My Company Page</div>
              <div className="preview-feed-time">Just now · 👥</div>
            </div>
          </div>
          <div className="preview-feed-body">
            {postContent || <span className="placeholder-text">Your Facebook post content will appear here...</span>}
          </div>
          {uploadedFiles.length > 0 && (
            <div className="preview-feed-media-grid">
              {uploadedFiles.map((file, idx) => (
                <img key={idx} src={file.preview} alt="upload preview" />
              ))}
            </div>
          )}
        </div>
      );
    }

    if (previewPlatform === "instagram") {
      return (
        <div className="preview-feed-card instagram">
          <div className="preview-feed-header">
            <div className="preview-feed-avatar insta">IG</div>
            <div>
              <div className="preview-feed-author">my_business_profile</div>
              <div className="preview-feed-time">Insta Feed Preview</div>
            </div>
          </div>
          <div className="preview-feed-instagram-media">
            {uploadedFiles.length > 0 ? (
              <img src={uploadedFiles[0].preview} alt="Instagram preview" />
            ) : (
              <div className="instagram-media-placeholder">
                <FiImage size={40} />
                <span>Instagram posts require an image/video</span>
              </div>
            )}
          </div>
          <div className="preview-feed-instagram-actions">
            <span>❤️ 💬 ✈️</span>
            <span>🔖</span>
          </div>
          <div className="preview-feed-body" style={{ padding: "0 14px 14px" }}>
            <strong>my_business_profile </strong>
            {postContent || <span className="placeholder-text">Caption text...</span>}
          </div>
        </div>
      );
    }

    if (previewPlatform === "linkedin") {
      return (
        <div className="preview-feed-card linkedin">
          <div className="preview-feed-header">
            <div className="preview-feed-avatar linkd">LI</div>
            <div>
              <div className="preview-feed-author">My Company Corporation</div>
              <div className="preview-feed-time">1st • Just now • 🌐</div>
            </div>
          </div>
          <div className="preview-feed-body">
            {postContent || <span className="placeholder-text">Your professional LinkedIn content goes here...</span>}
          </div>
          {uploadedFiles.length > 0 && (
            <div className="preview-feed-media-grid">
              <img src={uploadedFiles[0].preview} alt="LinkedIn preview" />
            </div>
          )}
        </div>
      );
    }
  };

  return (
    <div className="create-post-page">
      {/* Dynamic Top Hub Tabs */}
      <div className="content-hub-tabs">
        <button 
          className={`hub-tab-btn ${activeHubTab === "composer" ? "active" : ""}`}
          onClick={() => setActiveHubTab("composer")}
        >
          <FiFileText /> Composer
        </button>
        <button 
          className={`hub-tab-btn ${activeHubTab === "calendar" ? "active" : ""}`}
          onClick={() => setActiveHubTab("calendar")}
        >
          <FiCalendar /> Content Calendar
        </button>
        <button 
          className={`hub-tab-btn ${activeHubTab === "queue" ? "active" : ""}`}
          onClick={() => setActiveHubTab("queue")}
        >
          <FiLayers /> Queue & History
        </button>
      </div>

      {/* COMPOSER VIEW */}
      {activeHubTab === "composer" && (
        <>
          <div className="social-page-header">
            <div>
              <h1>Post Composer</h1>
              <p>Compose, upload media, preview, and schedule across all connected workspaces.</p>
            </div>
          </div>

          <div className="composer-container">
            {/* COMPOSER FORM */}
            <form className="create-post-form" onSubmit={handleSubmit}>
              {/* Channels Selector */}
              <div className="form-section">
                <label className="section-label"><FiGlobe style={{ marginRight: '6px' }} /> 1. Publish To</label>
                {loadingAccounts ? (
                  <p className="loading-text">Loading connected accounts...</p>
                ) : connectedAccounts.length === 0 ? (
                  <div className="no-accounts-alert">
                    <FiAlertCircle size={20} />
                    <div>
                      No connected social accounts found. Please connect an account first in the{" "}
                      <a href="/social-accounts">Social Accounts</a> page.
                    </div>
                  </div>
                ) : (
                  <div className="platform-selector">
                    {connectedAccounts.map((acc) => {
                      const isSelected = selectedAccountIds.includes(acc.id);
                      const isExpired = acc.expires_at && new Date(acc.expires_at) < new Date();
                      
                      return (
                        <button
                          type="button"
                          key={acc.id}
                          className={`platform-pill ${isSelected ? "active" : ""} ${isExpired ? "expired" : ""}`}
                          onClick={() => handleAccountToggle(acc.id)}
                        >
                          <span className="platform-icon">{getPlatformIcon(acc.platform)}</span>
                          <div className="platform-info-text">
                            <span className="acc-name">{acc.account_name}</span>
                            <span className="platform-tag">
                              {acc.platform} {isExpired && "⚠️ Expired"}
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Write Content */}
              <div className="form-section">
                <label className="section-label" htmlFor="postContent">
                  <FiFileText style={{ marginRight: '6px' }} /> 2. Write Post Content
                </label>
                <textarea
                  id="postContent"
                  rows="5"
                  value={postContent}
                  onChange={(e) => setPostContent(e.target.value)}
                  placeholder="What would you like to share today? Support tags #Marketing, mentions, links..."
                  maxLength={3000}
                />
                
                {/* Predefined Hashtags list */}
                <div className="hashtag-suggestions">
                  <span style={{ fontSize: "12px", color: "var(--text-muted)", marginRight: "6px" }}>Suggestions:</span>
                  {TRENDING_HASHTAGS.map((tag) => (
                    <button
                      type="button"
                      key={tag}
                      className="hashtag-pill"
                      onClick={() => handleHashtagClick(tag)}
                    >
                      {tag}
                    </button>
                  ))}
                </div>

                <div className="character-count">
                  {postContent.length} / 3000 characters
                </div>
              </div>

              {/* Media input & Drag Drop */}
              <div className="form-section">
                <label className="section-label">
                  <FiImage style={{ marginRight: '6px' }} /> 3. Attach Media
                </label>

                {/* Drag and Drop Zone */}
                <div 
                  className={`drag-drop-zone ${isDragOver ? "dragover" : ""}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <FiUploadCloud size={36} style={{ color: "var(--primary)" }} />
                  <p>Drag & Drop files here, or <span>Browse files</span></p>
                  <span className="file-limits">Support JPG, PNG, MP4 up to 10MB</span>
                  
                  <input
                    type="file"
                    ref={fileInputRef}
                    style={{ display: "none" }}
                    multiple
                    accept="image/*,video/*"
                    onChange={handleFileSelect}
                  />
                </div>

                {/* Import Media Cloud Sources */}
                <div className="import-cloud-wrapper">
                  <button 
                    type="button" 
                    className="import-cloud-btn" 
                    onClick={() => setShowImportModal(true)}
                  >
                    <FiFolderPlus /> Import from Cloud Sources
                  </button>
                </div>

                {/* Uploaded media previews */}
                {uploadedFiles.length > 0 && (
                  <div className="uploaded-files-list">
                    {uploadedFiles.map((file, idx) => (
                      <div key={idx} className="uploaded-file-card">
                        <img src={file.preview} alt="preview" />
                        <div className="uploaded-file-details">
                          <span className="file-name">{file.name}</span>
                          <span className="file-meta">{file.size} • {file.type.split("/")[1].toUpperCase()}</span>
                          {file.progress < 100 && (
                            <div className="progress-bar-container">
                              <div className="progress-bar-fill" style={{ width: `${file.progress}%` }}></div>
                            </div>
                          )}
                        </div>
                        <button 
                          type="button" 
                          className="remove-file-btn" 
                          onClick={() => handleRemoveFile(file.preview)}
                        >
                          <FiX />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Schedule settings */}
              <div className="form-section">
                <label className="section-label">
                  <FiClock style={{ marginRight: '6px' }} /> 4. Scheduling Options
                </label>
                <div className="schedule-options">
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="scheduleType"
                      value="now"
                      checked={scheduleType === "now"}
                      onChange={() => setScheduleType("now")}
                    />
                    Publish Now
                  </label>

                  <label className="radio-label">
                    <input
                      type="radio"
                      name="scheduleType"
                      value="queue"
                      checked={scheduleType === "queue"}
                      onChange={() => setScheduleType("queue")}
                    />
                    Add to Queue
                  </label>

                  <label className="radio-label">
                    <input
                      type="radio"
                      name="scheduleType"
                      value="schedule"
                      checked={scheduleType === "schedule"}
                      onChange={() => setScheduleType("schedule")}
                    />
                    Schedule Specific Time
                  </label>
                </div>

                {scheduleType === "queue" && nextQueueSlot && (
                  <div className="slot-suggestion">
                    <strong>Next available slot:</strong>{" "}
                    {new Date(nextQueueSlot).toLocaleString(undefined, {
                      dateStyle: "medium",
                      timeStyle: "short"
                    })}
                  </div>
                )}

                {scheduleType === "schedule" && (
                  <div className="date-picker-wrapper">
                    <input
                      type="datetime-local"
                      value={scheduleDate}
                      onChange={(e) => setScheduleDate(e.target.value)}
                      required
                    />
                  </div>
                )}
              </div>

              {/* Form Submit */}
              <div className="form-actions">
                <button type="submit" className="submit-btn" disabled={isSubmitting}>
                  {isSubmitting ? (
                    "Processing..."
                  ) : scheduleType === "now" ? (
                    <>
                      <FiSend style={{ marginRight: "6px" }} /> Publish Now
                    </>
                  ) : scheduleType === "queue" ? (
                    <>
                      <FiClock style={{ marginRight: "6px" }} /> Queue Post
                    </>
                  ) : (
                    <>
                      <FiClock style={{ marginRight: "6px" }} /> Schedule Post
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* LIVE PREVIEW CONTAINER */}
            <div className="composer-preview">
              <div className="preview-tabs">
                <button 
                  type="button" 
                  className={`preview-tab-btn ${previewPlatform === "facebook" ? "active" : ""}`}
                  onClick={() => setPreviewPlatform("facebook")}
                >
                  Facebook
                </button>
                <button 
                  type="button" 
                  className={`preview-tab-btn ${previewPlatform === "instagram" ? "active" : ""}`}
                  onClick={() => setPreviewPlatform("instagram")}
                >
                  Instagram
                </button>
                <button 
                  type="button" 
                  className={`preview-tab-btn ${previewPlatform === "linkedin" ? "active" : ""}`}
                  onClick={() => setPreviewPlatform("linkedin")}
                >
                  LinkedIn
                </button>
              </div>

              <div className="preview-card-wrapper">
                {renderPlatformSpecificPreview()}
              </div>

              {/* Character and Media validation Warnings */}
              <div className="validation-warnings">
                {previewPlatform === "instagram" && uploadedFiles.length === 0 && (
                  <span className="warning-text">⚠️ Instagram requires at least one image or video attachment to publish.</span>
                )}
                {previewPlatform === "linkedin" && postContent.length > 3000 && (
                  <span className="warning-text">⚠️ LinkedIn limits post characters to 3000.</span>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* CALENDAR HUB TAB */}
      {activeHubTab === "calendar" && (
        <div style={{ marginTop: "20px" }}>
          <Scheduler initialTab="calendar" />
        </div>
      )}

      {/* QUEUE & HISTORY HUB TAB */}
      {activeHubTab === "queue" && (
        <div style={{ marginTop: "20px" }}>
          <Scheduler initialTab="queue" />
        </div>
      )}

      {/* CLOUD IMPORT UNAVAILABLE MODAL */}
      {showImportModal && (
        <div className="connection-overlay">
          <div className="connection-modal" style={{ maxWidth: "450px" }}>
            <FiAlertCircle size={40} style={{ color: "var(--warning)", marginBottom: "15px" }} />
            <h2>Cloud Integration Missing</h2>
            <p style={{ fontSize: "14px", lineHeight: "1.6", color: "var(--text-secondary)" }}>
              External cloud integrations (such as Google Drive, Dropbox, or OneDrive) are not configured for this team. Please upload media directly from your computer using the Drag & Drop area.
            </p>
            <button 
              type="button" 
              className="modal-cancel-button" 
              style={{ width: "100%", marginTop: "15px" }} 
              onClick={() => setShowImportModal(false)}
            >
              Okay, Got it
            </button>
          </div>
        </div>
      )}

      {/* REAL-TIME STATUS MODAL */}
      {showStatusModal && publishingStatus && (
        <div className="connection-overlay">
          <div className="connection-modal" style={{ maxWidth: "500px", padding: "30px 24px" }}>
            <h2>Publishing Status</h2>
            <p>Publishing your post to selected channels in real-time.</p>

            <div className="status-list" style={{ textAlign: "left", margin: "20px 0" }}>
              {Object.keys(publishingStatus.channels).map((accId) => {
                const ch = publishingStatus.channels[accId];
                return (
                  <div
                    key={accId}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "12px",
                      borderRadius: "8px",
                      background: "rgba(255, 255, 255, 0.03)",
                      border: "1px solid var(--border-color)",
                      marginBottom: "10px"
                    }}
                  >
                    <div>
                      <strong style={{ display: "block", fontSize: "14px", color: "var(--text-primary)" }}>{ch.name}</strong>
                      <span style={{ fontSize: "12px", color: "var(--text-secondary)", textTransform: "capitalize" }}>{ch.platform}</span>
                    </div>

                    <div>
                      {ch.state === "publishing" && (
                        <span style={{ color: "var(--primary)", display: "flex", alignItems: "center", gap: "6px", fontSize: "13px" }}>
                          <FiRefreshCw className="spin" /> Publishing...
                        </span>
                      )}
                      {ch.state === "published" && (
                        <span style={{ color: "var(--success)", display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", fontWeight: "600" }}>
                          <FiCheck /> Published
                        </span>
                      )}
                      {ch.state === "failed" && (
                        <span
                          style={{ color: "var(--error)", display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", fontWeight: "600" }}
                          title={ch.error || "Publishing failed"}
                        >
                          <FiX /> Failed
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {Object.values(publishingStatus.channels).some(ch => ch.state === "failed") && (
              <div
                style={{
                  padding: "12px",
                  borderRadius: "8px",
                  background: "rgba(239, 68, 68, 0.05)",
                  border: "1px solid rgba(239, 68, 68, 0.2)",
                  color: "var(--error)",
                  fontSize: "13px",
                  textAlign: "left",
                  marginBottom: "20px"
                }}
              >
                <strong>Some channels failed to publish:</strong>
                <ul style={{ margin: "6px 0 0 0", padding: 0, listStyleType: "none" }}>
                  {Object.values(publishingStatus.channels)
                    .filter(ch => ch.state === "failed")
                    .map((ch, idx) => (
                      <li key={idx} style={{ marginBottom: "12px" }}>
                        <strong>{ch.name} ({ch.platform}):</strong>
                        {ch.platform === "facebook" ? (
                          <div style={{ marginTop: "4px" }}>
                            <div>Facebook couldn't publish this post.</div>
                            <div style={{ fontSize: "12px", opacity: 0.8, marginTop: "2px" }}>
                              The Facebook API rejected one of the publishing parameters.
                            </div>
                            <details style={{ marginTop: "6px" }}>
                              <summary style={{ cursor: "pointer", color: "var(--primary)", fontSize: "12px", outline: "none" }}>
                                View Details
                              </summary>
                              <div style={{
                                marginTop: "6px",
                                padding: "8px",
                                background: "rgba(0, 0, 0, 0.25)",
                                border: "1px solid rgba(255, 255, 255, 0.1)",
                                borderRadius: "4px",
                                fontSize: "12px",
                                color: "rgba(255, 255, 255, 0.8)",
                                wordBreak: "break-all"
                              }}>
                                {ch.error || "Invalid parameter"}
                              </div>
                            </details>
                          </div>
                        ) : (
                          <span style={{ marginLeft: "4px" }}>{ch.error || "Token expired or missing permissions."}</span>
                        )}
                      </li>
                    ))}
                </ul>
              </div>
            )}

            <div style={{ display: "flex", gap: "10px" }}>
              {(publishingStatus.status === "partially_published" || publishingStatus.status === "failed") && (
                <button
                  type="button"
                  onClick={handleRetryFailedOnly}
                  className="modal-connect-button"
                  style={{ flex: 1 }}
                >
                  Retry Failed
                </button>
              )}

              <button
                type="button"
                onClick={() => {
                  setShowStatusModal(false);
                  if (publishingStatus.status === "published") {
                    setPostContent("");
                    setSelectedAccountIds([]);
                    setUploadedFiles([]);
                    setScheduleType("now");
                    setScheduleDate("");
                  }
                }}
                className="modal-cancel-button"
                style={{ flex: 1, marginTop: 0 }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CreatePost;