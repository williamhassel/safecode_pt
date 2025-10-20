export default function GamePage() {
  return (
    <div style={{ textAlign: "center", marginTop: "2rem" }}>
      <h2>AI Vulnerability Challenge</h2>
      <iframe
        src="/godot/index.html"
        width="960"
        height="540"
        title="Godot Game"
        frameBorder="0"
        allowFullScreen
      />
    </div>
  );
}
