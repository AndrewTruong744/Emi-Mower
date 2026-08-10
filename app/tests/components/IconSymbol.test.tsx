import React from 'react';
import { render } from '@testing-library/react-native';
import { IconSymbol } from '@/components/ui/icon-symbol';

describe('IconSymbol', () => {
  it('renders a mapped platform icon', () => {
    const { getByTestId } = render(
      <IconSymbol name="house.fill" size={24} color="#000" testID="home-icon" />
    );
    expect(getByTestId('home-icon')).toBeTruthy();
  });
});
