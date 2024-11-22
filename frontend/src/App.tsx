import AudioMonitor from './components/AudioMonitor'

function App() {
  return (
    <div className="min-h-screen bg-gray-100 py-6 flex flex-col justify-center">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Baby Monitor</h1>
        </div>
        <AudioMonitor />
      </div>
    </div>
  )
}

export default App