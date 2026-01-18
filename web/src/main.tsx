import { render } from 'preact';
import { App } from './App';
import './index.css';

/**
 * Main entry point for the Motion Detector web application.
 * Renders the root App component into the DOM.
 */
const rootElement = document.getElementById('app');

if (rootElement) {
  render(<App />, rootElement);
} else {
  console.error('Root element not found. Unable to mount application.');
}
