// Minimal external store (zustand-style API) built on useSyncExternalStore.
// NOTE: `zustand` was intentionally hand-rolled here to keep the demo buildable
// in the offline field environment. Swap for `zustand` when it is available:
//   import { create } from "zustand";
import { useSyncExternalStore } from "react";

export function createStore<T>(initial: T) {
  let state = initial;
  const listeners = new Set<() => void>();

  const getState = () => state;
  const setState = (patch: Partial<T> | ((s: T) => Partial<T>)) => {
    const next = typeof patch === "function" ? (patch as (s: T) => Partial<T>)(state) : patch;
    state = { ...state, ...next };
    listeners.forEach((l) => l());
  };
  const subscribe = (l: () => void) => {
    listeners.add(l);
    return () => listeners.delete(l);
  };

  function useStore(): T;
  function useStore<S>(selector: (s: T) => S): S;
  function useStore<S>(selector?: (s: T) => S) {
    return useSyncExternalStore(
      subscribe,
      () => (selector ? selector(state) : (state as unknown as S)),
      () => (selector ? selector(state) : (state as unknown as S))
    );
  }

  return { getState, setState, subscribe, useStore };
}
