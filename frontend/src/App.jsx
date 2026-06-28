import { useEffect, useState } from "react";

function App() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    fetch("/api/finance/summary")
      .then((r) => r.json())
      .then(setSummary)
      .catch(console.error);
  }, []);

  return (
    <div>
      <h1>Finance App</h1>
      {summary ? (
        <pre>{JSON.stringify(summary, null, 2)}</pre>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  );
}

export default App;
