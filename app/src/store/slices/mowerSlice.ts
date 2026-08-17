import { StateCreator } from 'zustand';
import { BoundStoreState, MowerDetails, MowerSlice, MowerTelemetrySample } from '../types';

export const MOWER_TELEMETRY_MAX_SAMPLES = 60;

function defaultMowerName(uuid: string) {
  return `Mower ${uuid.slice(0, 8)}`;
}

function createMowerDetails(uuid: string, name = defaultMowerName(uuid)): MowerDetails {
  return {
    uuid,
    name,
    battery: null,
    state: 'unknown',
    health: 'unknown',
    telemetry: [],
  };
}

function mergeTelemetry(mower: MowerDetails, incoming: MowerTelemetrySample[]): MowerDetails {
  const telemetry = [...mower.telemetry, ...incoming]
    .sort((first, second) => first.timestamp - second.timestamp)
    .filter((sample, index, samples) => index === 0 || sample.timestamp !== samples[index - 1].timestamp)
    .slice(-MOWER_TELEMETRY_MAX_SAMPLES);
  const latestSample = telemetry.at(-1);

  if (!latestSample) return mower;

  return {
    ...mower,
    battery: latestSample.batteryPercentage,
    health: latestSample.slippageDetected ? 'attention' : 'healthy',
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
        mowerIds.map((uuid) => [uuid, state.mowerDetails[uuid] ?? createMowerDetails(uuid)])
      );
      const selectedMowerUuid = mowerIds.includes(state.selectedMowerUuid ?? '')
        ? state.selectedMowerUuid
        : (mowerIds[0] ?? null);

      const mowerPositions = Object.fromEntries(
        mowerIds.flatMap((uuid) =>
          state.mowerPositions[uuid] ? [[uuid, state.mowerPositions[uuid]]] : []
        )
      );

      return { mowers: mowerIds, mowerDetails, mowerPositions, selectedMowerUuid };
    });
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
          [normalizedUuid]: createMowerDetails(normalizedUuid, name?.trim() || defaultMowerName(normalizedUuid)),
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
  appendTelemetryBatch: (telemetryByMower) => {
    set((state) => {
      const entries = Object.entries(telemetryByMower).filter(
        ([uuid, telemetry]) => state.mowers.includes(uuid) && telemetry.length > 0
      );
      if (entries.length === 0) return state;

      const mowerDetails = { ...state.mowerDetails };
      const mowerPositions = { ...state.mowerPositions };
      for (const [uuid, telemetry] of entries) {
        const mower = mowerDetails[uuid];
        if (!mower) continue;
        mowerDetails[uuid] = mergeTelemetry(mower, telemetry);
        const newest = mowerDetails[uuid].telemetry.at(-1)!;
        mowerPositions[uuid] = { x: newest.longitude, y: newest.latitude };
      }
      return {
        mowerDetails,
        mowerPositions,
      };
    });
  },
  clearMowers: () => set({ mowers: [], mowerDetails: {}, mowerPositions: {}, selectedMowerUuid: null }),
});
