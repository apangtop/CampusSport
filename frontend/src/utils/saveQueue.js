export function createSaveQueue() {
  const tails = new Map()
  const pending = new Set()
  const failures = new Map()
  return {
    enqueue(key, task) {
      const previous = tails.get(key) || Promise.resolve()
      const promise = previous.catch(() => {}).then(task)
      tails.set(key, promise)
      pending.add(promise)
      promise.then(() => {
        pending.delete(promise)
        failures.delete(key)
        if (tails.get(key) === promise) tails.delete(key)
      }, error => {
        pending.delete(promise)
        failures.set(key, error)
        if (tails.get(key) === promise) tails.delete(key)
      })
      return promise
    },
    async flush() {
      while (pending.size) await Promise.allSettled([...pending])
      if (failures.size) throw failures.values().next().value
    },
    clearFailures() { failures.clear() }
  }
}
