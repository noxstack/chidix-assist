// Socket.IO Connection Setup
const socket = io("http://127.0.0.1:5000", {
    reconnectionAttempts: 3,
    transports: ["websocket"]
  });
  
  // DOM Elements
  const localVideo = document.getElementById("localVideo");
  const remoteVideo = document.getElementById("remoteVideo");
  const callBtn = document.getElementById("callBtn");
  const endCallBtn = document.getElementById("endCallBtn");
  const roomIdInput = document.getElementById("roomIdInput");
  const createRoomBtn = document.getElementById("createRoomBtn");
  const joinRoomBtn = document.getElementById("joinRoomBtn");
  const shareBtn = document.getElementById("shareBtn");
  const stopShareBtn = document.getElementById("stopShareBtn");
  const micBtn = document.getElementById("micBtn");
  const screenCaptureBtn = document.getElementById("screenCaptureBtn");
  const detectLanguageBtn = document.getElementById("detectLanguageBtn");
  const sourceLangSelect = document.getElementById("sourceLang");
  const targetLangSelect = document.getElementById("targetLang");
  const connectionStatusText = document.getElementById("connectionStatusText");
  const callStatus = document.getElementById("callStatus");
  const screenShareStatus = document.getElementById("screenShareStatus");
  const transcriptContainer = document.getElementById("transcriptContainer");
  
  // Global Variables
  let pc; // RTCPeerConnection
  let localStream;
  let screenStream;
  let roomId;
  let currentUser = "user_" + Math.random().toString(36).substring(2, 9);
  let audioContext;
  let audioProcessor;
  let isMicMuted = false;
  let isScreenSharing = false;
  
  // Initialize connection
  initializeConnection();
  
  function initializeConnection() {
    // Verify connection
    socket.on("connect", () => {
      console.log("Connected with ID:", socket.id);
      connectionStatusText.textContent = "Connected";
      connectionStatusText.style.color = "#4ade80";
    });
  
    socket.on("disconnect", () => {
      connectionStatusText.textContent = "Disconnected";
      connectionStatusText.style.color = "#f72585";
    });
  
    socket.on("connect_error", (err) => {
      console.error("Connection error:", err);
      connectionStatusText.textContent = "Connection failed";
      connectionStatusText.style.color = "#f72585";
    });
  
    // Room management
    createRoomBtn.addEventListener("click", createRoom);
    joinRoomBtn.addEventListener("click", joinRoom);
    callBtn.addEventListener("click", startCall);
    endCallBtn.addEventListener("click", endCall);
    shareBtn.addEventListener("click", startScreenShare);
    stopShareBtn.addEventListener("click", stopScreenShare);
    micBtn.addEventListener("click", toggleMicrophone);
    detectLanguageBtn.addEventListener("click", detectLanguage);
  
    // Initialize button states
    updateButtonStates();
  }
  
  // Room Management
  function createRoom() {
    roomId = roomIdInput.value || "room_" + Math.random().toString(36).substring(2, 7);
    socket.emit("create_room", { room_id: roomId, user_id: currentUser });
    roomIdInput.value = roomId;
    callStatus.textContent = `Room ${roomId} created`;
    updateButtonStates();
  }
  
  function joinRoom() {
    roomId = roomIdInput.value;
    if (!roomId) {
      callStatus.textContent = "Please enter a room ID";
      return;
    }
    socket.emit("join_room", { room_id: roomId, user_id: currentUser });
    callStatus.textContent = `Joining room ${roomId}...`;
    updateButtonStates();
  }
  
  // WebRTC Call Management
  async function startCall() {
    try {
      callStatus.textContent = "Starting call...";
      
      // Get user media
      localStream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true 
      });
      localVideo.srcObject = localStream;
  
      // Initialize audio processing for speech translation
      setupAudioProcessing();
  
      // Create peer connection
      pc = new RTCPeerConnection({
        iceServers: [
          { urls: "stun:stun.l.google.com:19302" },
          // Add TURN servers if needed for NAT traversal
        ]
      });
  
      // Add local stream tracks
      localStream.getTracks().forEach(track => {
        pc.addTrack(track, localStream);
      });
  
      // ICE candidate handling
      pc.onicecandidate = (event) => {
        if (event.candidate) {
          socket.emit("ice_candidate", {
            candidate: event.candidate,
            room_id: roomId,
            user_id: currentUser
          });
        }
      };
  
      // Remote stream handling
      pc.ontrack = (event) => {
        if (!remoteVideo.srcObject) {
          remoteVideo.srcObject = event.streams[0];
          callStatus.textContent = "Call connected";
        }
      };
  
      // Create offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      
      socket.emit("offer", {
        offer: offer,
        room_id: roomId,
        user_id: currentUser
      });
  
      updateButtonStates();
    } catch (err) {
      console.error("Error starting call:", err);
      callStatus.textContent = "Error starting call";
    }
  }
  
  function endCall() {
    // Close peer connection
    if (pc) {
      pc.close();
      pc = null;
    }
  
    // Stop local streams
    if (localStream) {
      localStream.getTracks().forEach(track => track.stop());
      localStream = null;
      localVideo.srcObject = null;
    }
  
    if (remoteVideo.srcObject) {
      remoteVideo.srcObject = null;
    }
  
    // Stop audio processing
    if (audioProcessor) {
      audioProcessor.disconnect();
      audioProcessor = null;
    }
  
    if (audioContext) {
      audioContext.close();
      audioContext = null;
    }
  
    callStatus.textContent = "Call ended";
    updateButtonStates();
  }
  
  // Screen Sharing
  async function startScreenShare() {
    try {
      screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false
      });
  
      const screenShareVideo = document.getElementById("screenShareVideo");
      screenShareVideo.srcObject = screenStream;
      document.getElementById("screenShareContainer").style.display = "block";
      
      // Add screen share track to peer connection
      if (pc) {
        screenStream.getTracks().forEach(track => {
          pc.addTrack(track, screenStream);
        });
      }
  
      isScreenSharing = true;
      screenShareStatus.textContent = "Screen sharing active";
      updateButtonStates();
  
      // Handle when user stops sharing via browser UI
      screenStream.getVideoTracks()[0].onended = () => {
        stopScreenShare();
      };
    } catch (err) {
      console.error("Error sharing screen:", err);
      screenShareStatus.textContent = "Screen sharing failed";
    }
  }
  
  function stopScreenShare() {
    if (screenStream) {
      screenStream.getTracks().forEach(track => track.stop());
      document.getElementById("screenShareContainer").style.display = "none";
      screenStream = null;
    }
    isScreenSharing = false;
    screenShareStatus.textContent = "";
    updateButtonStates();
  }
  
  // Audio Processing for Speech Translation
  function setupAudioProcessing() {
    if (!localStream || !localStream.getAudioTracks().length) return;
  
    audioContext = new AudioContext();
    const microphone = audioContext.createMediaStreamSource(localStream);
    audioProcessor = audioContext.createScriptProcessor(1024, 1, 1);
  
    microphone.connect(audioProcessor);
    audioProcessor.connect(audioContext.destination);
  
    audioProcessor.onaudioprocess = (e) => {
      if (!isMicMuted) {
        const audioData = e.inputBuffer.getChannelData(0);
        
        // For demo purposes, we'll send the audio every 3 seconds
        // In production, you'd want a more sophisticated buffering approach
        if (Math.random() < 0.1) { // 10% chance to send (simulating periodic sends)
          const audioBlob = new Blob([audioData], { type: 'audio/wav' });
          socket.emit("audio_blob", { 
            audio: audioBlob, 
            room_id: roomId,
            source_lang: sourceLangSelect.value,
            target_lang: targetLangSelect.value
          });
        }
      }
    };
  }
  
  // Language Detection
  function detectLanguage() {
    // In a real app, you'd send a sample of audio/text to the backend for detection
    // For now, we'll just simulate it
    const detectedLang = "en"; // Simulated detection
    sourceLangSelect.value = detectedLang;
    callStatus.textContent = `Detected language: ${getLanguageName(detectedLang)}`;
  }
  
  function getLanguageName(code) {
    const languages = {
      en: "English",
      es: "Spanish",
      fr: "French",
      de: "German",
      zh: "Chinese",
      ja: "Japanese"
    };
    return languages[code] || code;
  }
  
  // Microphone Control
  function toggleMicrophone() {
    if (!localStream) return;
    
    isMicMuted = !isMicMuted;
    localStream.getAudioTracks().forEach(track => {
      track.enabled = !isMicMuted;
    });
    
    micBtn.classList.toggle("active", isMicMuted);
    micBtn.title = isMicMuted ? "Unmute Microphone" : "Mute Microphone";
  }
  
  // Socket.IO Event Listeners
  socket.on("offer", async (data) => {
    if (!pc) {
      await startCall(); // Initialize our side if we haven't already
    }
    
    try {
      await pc.setRemoteDescription(new RTCSessionDescription(data.offer));
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      
      socket.emit("answer", {
        answer: answer,
        room_id: roomId,
        user_id: currentUser
      });
    } catch (err) {
      console.error("Error handling offer:", err);
    }
  });
  
  socket.on("answer", async (data) => {
    if (pc) {
      try {
        await pc.setRemoteDescription(new RTCSessionDescription(data.answer));
        callStatus.textContent = "Call connected";
      } catch (err) {
        console.error("Error handling answer:", err);
      }
    }
  });
  
  socket.on("ice_candidate", (data) => {
    if (pc && data.candidate) {
      pc.addIceCandidate(new RTCIceCandidate(data.candidate))
        .catch(err => console.error("Error adding ICE candidate:", err));
    }
  });
  
  socket.on("translation_result", (data) => {
    // Add translation to the transcript
    const messageDiv = document.createElement("div");
    messageDiv.className = "message message-incoming";
    messageDiv.innerHTML = `
      <div class="message-bubble incoming-bubble">
        <div class="message-text"><strong>Original:</strong> ${data.original}</div>
        <div class="message-text"><strong>Translated (${data.target_lang}):</strong> ${data.translated}</div>
        <div class="message-meta">${new Date().toLocaleTimeString()}</div>
      </div>
    `;
    transcriptContainer.appendChild(messageDiv);
    transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
  });
  
  socket.on("ocr_result", (data) => {
    // Display OCR translation overlay on screen share
    const screenContainer = document.getElementById("screenShareContainer");
    
    // Remove existing overlays
    document.querySelectorAll(".ocr-translation").forEach(el => el.remove());
    
    // Create new overlay (simplified - in reality you'd position based on OCR coordinates)
    if (data.translated && screenContainer.style.display !== "none") {
      const overlay = document.createElement("div");
      overlay.className = "ocr-translation";
      overlay.textContent = data.translated;
      overlay.style.left = "50px";
      overlay.style.top = "50px";
      screenContainer.appendChild(overlay);
    }
  });
  
  socket.on("user_joined", (data) => {
    callStatus.textContent = `${data.user_id} joined the room`;
  });
  
  socket.on("user_left", (data) => {
    callStatus.textContent = `${data.user_id} left the room`;
  });
  
  // UI Helper Functions
  function updateButtonStates() {
    const isInRoom = !!roomId;
    const isCallActive = !!pc;
    
    // Room buttons
    createRoomBtn.disabled = false;
    joinRoomBtn.disabled = !roomIdInput.value;
    
    // Call buttons
    callBtn.disabled = !isInRoom || isCallActive;
    endCallBtn.disabled = !isCallActive;
    
    // Media buttons
    shareBtn.disabled = !isCallActive;
    stopShareBtn.disabled = !isScreenSharing;
    screenCaptureBtn.disabled = !isScreenSharing;
    
    // Mic button state reflects current mute status
    micBtn.disabled = !isCallActive;
    micBtn.classList.toggle("active", isMicMuted);
  }
  
  // Initialize
  updateButtonStates();