import "./globals.css";

export const metadata = {
  title: "Law Script Translation",
  description: "English legal text to Kannada and Konkani, for legal awareness.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
