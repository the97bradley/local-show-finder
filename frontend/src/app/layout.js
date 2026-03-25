import "./globals.css";

export const metadata = {
  title: "Local Show Finder",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
