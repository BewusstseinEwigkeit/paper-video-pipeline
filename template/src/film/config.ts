// Per-film settings. Everything project-specific that the shared shell (captions, chapter marks, audio) needs.
export const CFG = {
  // chapter marks (top-left): [first line id of the chapter, label]; an empty label hides the marks from there on
  sections: [
    ["b1", "Background"],
    ["p1", "Problem"],
    ["m1", "Method"],
    ["r1", "Results"],
    ["e1", ""],
  ] as Array<[string, string]>,
  // caption keyword colours, one meaning per colour (matched per caption token: English words, or Latin terms inside Chinese)
  captionKeywords: [
    [["uncertain"], "#F87171"],
    [["surroundings"], "#6EA2FF"],
  ] as Array<[string[], string]>,
  // method / module names: cyan italic in captions
  methodWords: ["XYZ"],
  // lines that a card shows verbatim: no caption underneath (avoid saying the same words twice on screen)
  silentLines: ["c0a", "p1", "e1"],
  // soft light leak at each chapter boundary (src/kit/ChapterLeak.tsx)
  chapterLeak: true,
  // final mix produced by tools/mix_all.py; null renders silent (e.g. while blocking with fake_timeline.py)
  audio: null as string | null, // e.g. "audio/final.wav"
};
