import React from 'react';
import { render } from '@testing-library/react-native';
import { PaperProvider } from 'react-native-paper';
import Controller from '@/app/(tabs)/controller';

describe('Controller screen', () => {
  it('renders the controller area and controls', () => {
    const { getByText } = render(
      <PaperProvider>
        <Controller />
      </PaperProvider>
    );
    expect(getByText('E-STOP')).toBeTruthy();
  });
});
