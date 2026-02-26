import './globals.css';

export const metadata = {
  title: 'SEOULFIT — AI Korean Fashion',
  description: 'AI가 큐레이션하는 한국 패션 플랫폼',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}