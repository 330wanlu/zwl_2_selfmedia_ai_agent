import { create } from 'zustand'

type UiState = {
  listVersion: number
  bumpList: () => void
}

/** 列表页在创建任务后可 bump，触发重新拉取 */
export const useUiStore = create<UiState>((set) => ({
  listVersion: 0,
  bumpList: () => set((s) => ({ listVersion: s.listVersion + 1 })),
}))
