import React from 'react';

export const metadata = {
  title: 'ACT',
  description: 'Airport & City Group',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta
          name="google-site-verification"
          content="-JqU021-FySgKIvmSaumQHIfWj7G5DqRJurNdON7xOc"
        />
      </head>

      <body>{children}</body>
    </html>
  );
}
