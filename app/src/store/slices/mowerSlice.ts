import { StateCreator } from 'zustand';
import { BoundStoreState, MowerDetails, MowerSlice, MowerTelemetrySample } from '../types';

export const MOWER_TELEMETRY_MAX_SAMPLES = 60;
export const MOWER_TELEMETRY_INTERVAL_MS = 500;

const DEFAULT_FAKE_MOWERS = [
  { uuid: 'a0f6f58e-ef97-4fa9-aede-002467ca11ed', name: 'Backyard Mower' },
  { uuid: '7c3d863b-5778-4ae6-9177-151d2f9f846d', name: 'Front Yard Mower' },
  { uuid: 'f1a65c4e-bc14-467c-a16b-2e9f0c4bb2ef', name: 'Orchard Mower' },
  { uuid: '8e2c3f16-33fd-493b-a58f-5f7d7dbfe0e0', name: 'Side Yard Mower' },
  { uuid: 'c06da1dc-2e95-4db1-87ef-d73084d7e509', name: 'Garden Mower' },
  { uuid: '315a474f-d2b1-4116-819f-3df198f9501a', name: 'North Field Mower' },
];

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
}

function mowerSeed(uuid: string) {
  return Array.from(uuid).reduce((total, character) => total + character.charCodeAt(0), 0);
}

function defaultMowerName(uuid: string) {
  return `Mower ${uuid.slice(0, 8)}`;
}

function createInitialPosition(uuid: string) {
  const seed = mowerSeed(uuid);
  return {
    x: -74.006 + ((seed % 17) - 8) * 0.00003,
    y: 40.7128 + ((seed % 13) - 6) * 0.00003,
  };
}

function createFakeTelemetry(uuid: string, timestamp: number, index: number): MowerTelemetrySample {
  const seed = mowerSeed(uuid);
  const phase = index + timestamp / 1_000 + seed / 20;
  const direction = Math.sin(phase / 8) > -0.85 ? 1 : 0;

  return {
    timestamp,
    latitude: Number((40.7128 + Math.sin(phase / 70) * 0.0002).toFixed(7)),
    longitude: Number((-74.006 + Math.cos(phase / 70) * 0.0002).toFixed(7)),
    batteryPercentage: Number(clamp(62 + (seed % 35) - index * 0.01, 0, 100).toFixed(2)),
    leftMotorSpeed: Number(clamp(0.62 + Math.sin(phase / 2.2) * 0.35, 0, 1).toFixed(2)),
    leftMotorDirection: direction,
    rightMotorSpeed: Number(clamp(0.62 + Math.cos(phase / 2.1) * 0.35, 0, 1).toFixed(2)),
    rightMotorDirection: direction,
    cuttingMotorSpeed: Math.round(clamp(2_750 + Math.sin(phase / 1.7) * 420, 0, 3_500)),
    slippageDetected: Math.sin(phase / 4.5) > 0.91,
    imuData: {
      accelX: Number((Math.sin(phase / 1.5) * 0.35).toFixed(2)),
      accelY: Number((Math.cos(phase / 1.8) * 0.35).toFixed(2)),
      accelZ: Number((9.81 + Math.sin(phase / 1.3) * 0.25).toFixed(2)),
      gyroX: Number((Math.sin(phase / 2.1) * 0.18).toFixed(2)),
      gyroY: Number((Math.cos(phase / 1.9) * 0.18).toFixed(2)),
      gyroZ: Number((Math.sin(phase / 2.4) * 0.22).toFixed(2)),
      magX: Number((22 + Math.sin(phase / 2.5) * 3).toFixed(2)),
      magY: Number((-4 + Math.cos(phase / 2.6) * 2).toFixed(2)),
      magZ: Number((41 + Math.sin(phase / 2.7) * 3).toFixed(2)),
    },
  };
}

function createFakeMower(uuid: string, name = defaultMowerName(uuid)): MowerDetails {
  const seed = mowerSeed(uuid);
  const now = Date.now();
  const telemetry = Array.from({ length: MOWER_TELEMETRY_MAX_SAMPLES }, (_, index) =>
    createFakeTelemetry(
      uuid,
      now - (MOWER_TELEMETRY_MAX_SAMPLES - 1 - index) * MOWER_TELEMETRY_INTERVAL_MS,
      index
    )
  );

  return {
    uuid,
    name,
    battery: 62 + (seed % 35),
    state: seed % 5 === 0 ? 'stopped' : seed % 2 === 0 ? 'on' : 'off',
    health: seed % 7 === 0 ? 'attention' : 'healthy',
    telemetry,
  };
}

function normalizeMowerIds(mowers: string[]) {
  return [...new Set(mowers.map((mower) => mower.trim()).filter(Boolean))];
}

export const createMowerSlice: StateCreator<BoundStoreState, [], [], MowerSlice> = (set, get) => ({
  mowers: [],
  mowerDetails: {},
  mowerPositions: {},
  selectedMowerUuid: null,
  setMowers: (mowers) => {
    const mowerIds = normalizeMowerIds(mowers);
    set((state) => {
      const mowerDetails = Object.fromEntries(
        mowerIds.map((uuid) => [uuid, state.mowerDetails[uuid] ?? createFakeMower(uuid)])
      );
      const selectedMowerUuid = mowerIds.includes(state.selectedMowerUuid ?? '')
        ? state.selectedMowerUuid
        : (mowerIds[0] ?? null);

      const mowerPositions = Object.fromEntries(
        mowerIds.map((uuid) => [uuid, state.mowerPositions[uuid] ?? createInitialPosition(uuid)])
      );

      return { mowers: mowerIds, mowerDetails, mowerPositions, selectedMowerUuid };
    });
  },
  seedFakeMowers: () => {
    if (get().mowers.length > 0) return;
    const mowerIds = DEFAULT_FAKE_MOWERS.map((mower) => mower.uuid);
    const mowerDetails = Object.fromEntries(
      DEFAULT_FAKE_MOWERS.map(({ uuid, name }) => [uuid, createFakeMower(uuid, name)])
    );
    const mowerPositions = Object.fromEntries(
      mowerIds.map((uuid) => [uuid, createInitialPosition(uuid)])
    );
    set({ mowers: mowerIds, mowerDetails, mowerPositions, selectedMowerUuid: mowerIds[0] });
  },
  addMower: (uuid, name) => {
    const normalizedUuid = uuid.trim();
    if (!normalizedUuid) return;

    set((state) => {
      if (state.mowers.includes(normalizedUuid)) {
        return { selectedMowerUuid: normalizedUuid };
      }

      return {
        mowers: [...state.mowers, normalizedUuid],
        mowerDetails: {
          ...state.mowerDetails,
          [normalizedUuid]: createFakeMower(normalizedUuid, name?.trim() || defaultMowerName(normalizedUuid)),
        },
        mowerPositions: {
          ...state.mowerPositions,
          [normalizedUuid]: createInitialPosition(normalizedUuid),
        },
        selectedMowerUuid: normalizedUuid,
      };
    });
  },
  renameMower: (uuid, name) => {
    const trimmedName = name.trim();
    if (!trimmedName) return;

    set((state) => {
      const mower = state.mowerDetails[uuid];
      if (!mower) return state;
      return {
        mowerDetails: {
          ...state.mowerDetails,
          [uuid]: { ...mower, name: trimmedName },
        },
      };
    });
  },
  selectMower: (uuid) => {
    if (get().mowers.includes(uuid)) set({ selectedMowerUuid: uuid });
  },
  appendFakeTelemetry: (uuid) => {
    set((state) => {
      const mower = state.mowerDetails[uuid];
      if (!mower) return state;

      const telemetry = [
        ...mower.telemetry,
        createFakeTelemetry(uuid, Date.now(), mower.telemetry.length),
      ].slice(-MOWER_TELEMETRY_MAX_SAMPLES);
      const latestSample = telemetry.at(-1)!;

      return {
        mowerDetails: {
          ...state.mowerDetails,
          [uuid]: {
            ...mower,
            battery: latestSample.batteryPercentage,
            health: latestSample.slippageDetected ? 'attention' : mower.health,
            telemetry,
          },
        },
      };
    });
  },
  placeMowersInBoundary: (boundary) => {
    if (boundary.length < 3) return;
    const xValues = boundary.map((point) => point.x);
    const yValues = boundary.map((point) => point.y);
    const minX = Math.min(...xValues);
    const maxX = Math.max(...xValues);
    const minY = Math.min(...yValues);
    const maxY = Math.max(...yValues);

    set((state) => ({
      mowerPositions: Object.fromEntries(
        state.mowers.map((uuid) => {
          const seed = mowerSeed(uuid);
          return [
            uuid,
            {
              x: minX + (maxX - minX) * (((seed % 89) + 5) / 100),
              y: minY + (maxY - minY) * ((((seed * 7) % 89) + 5) / 100),
            },
          ];
        })
      ),
    }));
  },
  advanceFakeMowerPositions: () => {
    set((state) => ({
      mowerPositions: Object.fromEntries(
        state.mowers.map((uuid, index) => {
          const position = state.mowerPositions[uuid] ?? createInitialPosition(uuid);
          const phase = Date.now() / 1_000 + index;
          return [
            uuid,
            {
              x: position.x + Math.cos(phase) * 0.0000015,
              y: position.y + Math.sin(phase) * 0.0000015,
            },
          ];
        })
      ),
    }));
  },
  clearMowers: () => set({ mowers: [], mowerDetails: {}, mowerPositions: {}, selectedMowerUuid: null }),
});
