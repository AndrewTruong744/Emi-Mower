import React from 'react';
import { beforeEach, describe, expect, it } from '@jest/globals';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import { createWrapper, mockedZenohQuery, resetHookState } from '../hooks/testUtils';
import { Livestream } from '@/components/controller/Livestream';

describe('Livestream', () => {
  beforeEach(resetHookState);

  function renderLivestream(mowerId: string | null = 'mower-1') {
    const QueryWrapper = createWrapper();
    return render(
      <PaperProvider>
        <QueryWrapper>
          <Livestream mowerId={mowerId} />
        </QueryWrapper>
      </PaperProvider>
    );
  }

  it('connects with viewer credentials and clears them on disconnect', async () => {
    mockedZenohQuery.mockResolvedValue({
      token: 'viewer-token',
      url: 'wss://livekit.test',
      expires_in: 3600,
    });
    const screen = renderLivestream();

    fireEvent.press(screen.getByTestId('livestream-toggle'));
    await waitFor(() => expect(screen.getByTestId('livestream-preview')).toBeTruthy());
    expect(mockedZenohQuery).toHaveBeenCalledWith('mower/mower-1/livekit/consume', {});

    fireEvent.press(screen.getByTestId('livestream-toggle'));
    expect(screen.queryByTestId('livestream-preview')).toBeNull();
  });

  it('does not connect without a selected mower and displays a credential error', async () => {
    const noMowerScreen = renderLivestream(null);
    fireEvent.press(noMowerScreen.getByTestId('livestream-toggle'));
    expect(mockedZenohQuery).not.toHaveBeenCalled();

    mockedZenohQuery.mockRejectedValue(new Error('Viewer token denied'));
    const screen = renderLivestream();
    fireEvent.press(screen.getByTestId('livestream-toggle'));
    await waitFor(() => expect(screen.getByText('Viewer token denied')).toBeTruthy());
  });
});
