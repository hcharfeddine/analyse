import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Citation Network Visualization',
  description: 'Interactive visualization of scientific paper citation networks',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
