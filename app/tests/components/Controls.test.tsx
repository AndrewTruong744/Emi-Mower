import React from 'react';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { Alert } from 'react-native';
import { act, fireEvent, render } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import { __mockGesture } from '../mocks/gesture-handler';
import { createWrapper, mockedZenohQuery, resetHookState } from '../hooks/testUtils';
import Controls from '@/components/controller/Controls';

describe('Controls', () => {
  beforeEach(resetHookState);

  it('renders the mower controls', () => {
    const QueryWrapper = createWrapper();
    const { getByText } = render(
      <PaperProvider>
        <QueryWrapper>
          <Controls mowerId="mower-1" />
        </QueryWrapper>
      </PaperProvider>
    );
    expect(getByText('E-STOP')).toBeTruthy();
    expect(getByText('SYS: OFF')).toBeTruthy();
    expect(getByText('MAN')).toBeTruthy();
  });

  it('updates power, autonomous mode, and emergency stop after the mower accepts each command', async () => {
    mockedZenohQuery.mockImplementation(async (_path, payload) => ({
      command_id: payload.command_id,
      status: 'accepted',
    }));
    const QueryWrapper = createWrapper();
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const { getByText, getAllByRole } = render(
      <PaperProvider>
        <QueryWrapper>
          <Controls mowerId="mower-1" />
        </QueryWrapper>
      </PaperProvider>
    );

    await act(async () => {
      fireEvent(getAllByRole('switch')[0], 'valueChange', true);
    });
    await act(async () => {
      fireEvent(getAllByRole('switch')[1], 'valueChange', true);
    });
    expect(getByText('SYS: ON')).toBeTruthy();
    expect(getByText('AUTO')).toBeTruthy();

    await act(async () => {
      fireEvent.press(getByText('E-STOP'));
    });
    expect(getByText('STOPPED')).toBeTruthy();
    expect(getByText('SYS: OFF')).toBeTruthy();

    expect(alertSpy).toHaveBeenCalled();
    alertSpy.mockRestore();
  });

  it('normalizes joystick movement and returns it to center', () => {
    const QueryWrapper = createWrapper();
    const { getByText } = render(
      <PaperProvider>
        <QueryWrapper>
          <Controls mowerId="mower-1" />
        </QueryWrapper>
      </PaperProvider>
    );
    expect(getByText('E-STOP')).toBeTruthy();
    expect(__mockGesture.updateCallback).toEqual(expect.any(Function));
    expect(__mockGesture.endCallback).toEqual(expect.any(Function));
    (__mockGesture.updateCallback as unknown as (event: { translationX: number; translationY: number }) => void)({
      translationX: 100,
      translationY: -100,
    });
    (__mockGesture.endCallback as unknown as () => void)();

  });

  it('disables manual controls until a mower is selected', () => {
    const QueryWrapper = createWrapper();
    const screen = render(
      <PaperProvider>
        <QueryWrapper>
          <Controls mowerId={null} />
        </QueryWrapper>
      </PaperProvider>
    );

    fireEvent.press(screen.getByTestId('controller-estop'));
    fireEvent(screen.getAllByRole('switch')[0], 'valueChange', true);
    fireEvent(screen.getAllByRole('switch')[1], 'valueChange', true);
    (__mockGesture.updateCallback as unknown as (event: { translationX: number; translationY: number }) => void)({
      translationX: 100,
      translationY: -100,
    });

    expect(screen.getByText('E-STOP')).toBeTruthy();
    expect(screen.getByText('SYS: OFF')).toBeTruthy();
    expect(screen.getByText('MAN')).toBeTruthy();
  });
});
