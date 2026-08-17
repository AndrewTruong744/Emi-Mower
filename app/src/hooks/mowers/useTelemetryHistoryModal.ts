import { useCallback, useEffect, useMemo, useState } from 'react';
import { useMowerTelemetryHistory } from '@/hooks/api/mower/useMowerTelemetryHistory';
import { MetricChartProps } from '@/components/mowers/MetricChart';

interface TelemetryHistoryPage {
  values: number[];
  hasMore: boolean;
  nextCursor: string | null;
}

interface UseTelemetryHistoryModalOptions {
  chart: MetricChartProps;
  mowerId: string;
}

/** Cursor-pagination state for the focused telemetry modal. */
export function useTelemetryHistoryModal({ chart, mowerId }: UseTelemetryHistoryModalOptions) {
  const [historyPages, setHistoryPages] = useState<TelemetryHistoryPage[]>([]);
  const [page, setPage] = useState(0);
  const [requestedCursor, setRequestedCursor] = useState<string | null | undefined>(undefined);
  const telemetryType = chart.telemetryType ?? '';
  const requestEnabled = requestedCursor !== undefined;
  const query = useMowerTelemetryHistory({
    mowerId,
    telemetryType,
    cursor: requestedCursor ?? null,
    enabled: requestEnabled,
  });

  useEffect(() => {
    setHistoryPages([]);
    setPage(0);
    setRequestedCursor(undefined);
  }, [mowerId, telemetryType]);

  useEffect(() => {
    if (!requestEnabled || !query.data) return;
    const pageData: TelemetryHistoryPage = {
      // The backend returns newest-first; charts display oldest-to-newest.
      values: query.data.points.map((point) => point.value).reverse(),
      hasMore: query.data.has_more,
      nextCursor: query.data.next_cursor,
    };
    setHistoryPages((pages) => [...pages, pageData]);
    setPage((currentPage) => currentPage + 1);
    setRequestedCursor(undefined);
  }, [query.data, requestEnabled]);

  const pages = useMemo(() => [chart.values, ...historyPages.map((historyPage) => historyPage.values)], [chart.values, historyPages]);
  const currentHistoryPage = historyPages.at(-1);
  const canViewNewer = page > 0;
  const canViewOlder =
    !query.isFetching &&
    (page < historyPages.length || historyPages.length === 0 || currentHistoryPage?.hasMore === true);

  const viewNewer = useCallback(() => setPage((currentPage) => Math.max(0, currentPage - 1)), []);
  const viewOlder = useCallback(() => {
    if (page < historyPages.length) {
      setPage((currentPage) => currentPage + 1);
      return;
    }
    if (query.isFetching || (currentHistoryPage && !currentHistoryPage.hasMore)) return;
    setRequestedCursor(currentHistoryPage?.nextCursor ?? null);
  }, [currentHistoryPage, historyPages.length, page, query.isFetching]);

  return {
    canViewNewer,
    canViewOlder,
    isLoadingOlder: query.isFetching,
    page,
    pages,
    viewNewer,
    viewOlder,
  };
}
