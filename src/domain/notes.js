// Vrstni red zapisov in sosedje; čista logika brez shrambe in DOM.

// Datum ima natančnost minute, zato pri istem datumu odloči čas nastanka.
export function sortNotes(notes) {
  return [...notes].sort((a, b) =>
    a.date < b.date ? -1 : a.date > b.date ? 1 : (a.created || 0) - (b.created || 0),
  );
}

/** Prejšnji in naslednji zapis od `currentId` v že urejenem seznamu. */
export function neighbours(notes, currentId) {
  const sorted = sortNotes(notes);
  const index = sorted.findIndex((n) => n.id === currentId);
  if (index < 0)
    return { previous: null, next: null, index: -1, total: sorted.length, isNewest: false };
  return {
    previous: sorted[index - 1] || null,
    next: sorted[index + 1] || null,
    index,
    total: sorted.length,
    isNewest: index === sorted.length - 1,
  };
}
