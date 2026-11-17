// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { Button, Feedback, Status } from './ui';

afterEach(cleanup);

test('button executes an available action and disables an in-flight action', () => {
  const click = vi.fn();
  const view = render(<Button onClick={click}>Verify closure</Button>);
  fireEvent.click(screen.getByRole('button'));
  view.rerender(<Button onClick={click} disabled>Verify closure</Button>);
  fireEvent.click(screen.getByRole('button'));
  expect(click).toHaveBeenCalledTimes(1);
});

test('reports a blocked closure as an accessible alert', () => {
  render(<Feedback message="Required completion evidence is missing." error />);
  expect(screen.getByRole('alert').textContent).toContain('completion evidence is missing');
});

test('renders normalized clinical states with a readable label', () => {
  render(<Status value="missing_closure_evidence" />);
  expect(screen.getByText('Missing closure evidence')).toBeTruthy();
});
