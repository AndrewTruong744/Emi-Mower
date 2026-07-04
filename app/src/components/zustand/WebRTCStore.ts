import { create } from 'zustand';
import { io, Socket } from 'socket.io-client';
import { RTCPeerConnection, MediaStream, RTCSessionDescription, RTCIceCandidate } from 'react-native-webrtc';

interface WebRTCState {
  remoteStream: MediaStream | null;
  isConnected: boolean;
  isConnecting: boolean;
  initiateSocketAndConnect: (socketUrl: string, roomId: string) => void;
  disconnect: () => void;
  sendControlData: (data: object) => void;
}

const WEBRTC_CONFIG = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
  ],
};

let socketClient: Socket | null = null;
let peerConnection: RTCPeerConnection | null = null;
let dataChannel: RTCDataChannel | null = null;

export const useWebRTCStore = create<WebRTCState>((set, get) => ({
  remoteStream: null,
  isConnected: false,
  isConnecting: false,

  initiateSocketAndConnect: (socketUrl: string, roomId: string) => {
    if (peerConnection || get().isConnected) return;
    set({ isConnecting: true });

    // 1. Initialize Socket.io Client Connection
    socketClient = io(socketUrl, { transports: ['websocket'] });

    socketClient.on('connect', () => {
      console.log('Signaling Socket Connected! Joining Room:', roomId);
      socketClient?.emit('join-room', { room: roomId });
    });

    // 2. Initialize the Local WebRTC Peer Connection Object
    const pc = new RTCPeerConnection(WEBRTC_CONFIG);
    const pcAny = pc as any;
    peerConnection = pc;

    // 4. Handle Incoming Network Routes (ICE Candidates) from your Phone's Radio
    pcAny.onicecandidate = (event: any) => {
      if (event.candidate) {
        socketClient?.emit('signal-ice-candidate', {
          room: roomId,
          candidate: event.candidate,
        });
      }
    };

    // 5. Catch Incoming Video Stream from the Robot
    pcAny.ontrack = (event: any) => {
      if (event.streams && event.streams[0]) {
        set({ remoteStream: event.streams[0] });
      }
    };

    // ==========================================
    // SOCKET.IO SIGNALING EVENT LISTENERS
    // ==========================================

    // Listen for the Robot's Answer SDP
    socketClient.on('webrtc-answer', async (data: { sdp: string }) => {
      try {
        await pc.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: data.sdp }));
        console.log('Remote Answer Applied Successfully ✅');
      } catch (err) {
        console.error('Error applying remote answer SDP:', err);
      }
    });

    // Listen for incoming ICE network routes sent out by the Robot
    socketClient.on('robot-ice-candidate', async (data: { candidate: any }) => {
      try {
        if (pc.remoteDescription) {
          await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
        }
      } catch (err) {
        console.error('Failed to add remote ICE candidate:', err);
      }
    });

    // Trigger the Handshake once the Socket loop settles
    const negotiateHandshake = async () => {
      try {
        const offer = await pc.createOffer({});
        await pc.setLocalDescription(offer);

        // Emit your phone's Local SDP Offer to the robot room channel
        socketClient?.emit('signal-offer', {
          room: roomId,
          sdp: offer.sdp,
        });
      } catch (err) {
        console.error('Failed generating handshake SDP offer:', err);
        get().disconnect();
      }
    };

    negotiateHandshake();
  },

  disconnect: () => {
    if (dataChannel) dataChannel.close();
    if (peerConnection) peerConnection.close();
    if (socketClient) {
      socketClient.disconnect();
      socketClient = null;
    }

    peerConnection = null;
    dataChannel = null;

    set({ remoteStream: null, isConnected: false, isConnecting: false });
    console.log('WebRTC and Socket Sessions Disconnected completely.');
  },

  sendControlData: (data: object) => {
    if (dataChannel && dataChannel.readyState === 'open') {
      dataChannel.send(JSON.stringify(data));
    }
  },
}));