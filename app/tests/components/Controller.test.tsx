import React from 'react';
import { beforeEach, describe, expect, it } from '@jest/globals';
import { render } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import { createWrapper, resetHookState } from '../hooks/testUtils';
import Controller from '@/app/(tabs)/controller';

describe('Controller screen', () => {
  beforeEach(resetHookState);

  it('renders the controller area and controls', () => {
    const QueryWrapper = createWrapper();
    const { getByText, queryByText } = render(
      <PaperProvider>
        <QueryWrapper>
          <Controller />
        </QueryWrapper>
      </PaperProvider>
    );
    expect(getByText('Livestream')).toBeTruthy();
    expect(getByText('E-STOP')).toBeTruthy();
    expect(queryByText('Controller')).toBeNull();
    expect(queryByText('Manual controls')).toBeNull();
  });
});
