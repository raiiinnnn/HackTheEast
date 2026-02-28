import { create } from "zustand";
import { CourseResponse } from "../api/types";

interface AppState {
  courses: CourseResponse[];
  currentCourse: CourseResponse | null;
  setCourses: (courses: CourseResponse[]) => void;
  setCurrentCourse: (course: CourseResponse | null) => void;
  addCourse: (course: CourseResponse) => void;
}

export const useAppStore = create<AppState>((set) => ({
  courses: [],
  currentCourse: null,
  setCourses: (courses) => set({ courses }),
  setCurrentCourse: (course) => set({ currentCourse: course }),
  addCourse: (course) =>
    set((state) => ({ courses: [course, ...state.courses] })),
}));
