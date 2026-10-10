export const MALE_NAMES = [
  "Jose Miguel Reyes",
  "Juan Carlos Santos",
  "Rafael Angelo Cruz",
  "Miguel Antonio Garcia",
  "Carlos Eduardo Bautista",
  "Angelo Luis Mendoza",
  "Pedro Javier Rodriguez",
  "Roberto Emilio Aquino",
  "Francisco Dela Cruz",
  "Andres Paolo Lopez",
  "Nathaniel Reyes",
  "Joshua Miguel Santos",
  "Adrian Cruz",
  "Matthew Garcia",
  "Lorenzo Bautista",
  "Gabriel Mendoza",
  "Rafael Santos",
  "Daniel Aquino",
  "Kenneth Dela Cruz",
  "Vincent Rodriguez",
  "Marco Fernandez",
  "Luis Morales",
  "Ramon Villanueva",
  "Diego Ramos",
  "Samuel Gonzales",
];

export const FEMALE_NAMES = [
  "Maria Elena Reyes",
  "Ana Patricia Santos",
  "Sophia Isabel Cruz",
  "Cristina Mae Garcia",
  "Beatriz Angela Bautista",
  "Andrea Nicole Mendoza",
  "Jasmine Reyes",
  "Katrina Santos",
  "Isabella Cruz",
  "Angelica Lopez",
  "Patricia Aquino",
  "Daniela Fernandez",
  "Sophia Morales",
  "Mikaela Dela Cruz",
  "Alessandra Rodriguez",
  "Lauren Bautista",
  "Hannah Garcia",
  "Nicole Villanueva",
  "Samantha Ramos",
  "Adrienne Gonzales",
  "Julia Perez",
  "Camille Torres",
  "Francesca Rivera",
  "Mariel Santos",
  "Bianca Mendoza",
];

const DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"];

export type Name = [name: string, gender: "Male" | "Female"];

/** Shuffled pool of (name, gender). No repeats until the pool is exhausted. */
export function buildNamePool(): Name[] {
  const pool: Name[] = [
    ...MALE_NAMES.map((n) => [n, "Male"] as Name),
    ...FEMALE_NAMES.map((n) => [n, "Female"] as Name),
  ];
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]] as [Name, Name];
  }
  return pool;
}

/** Realistic email derived from a name, like the desktop bot. */
export function generateEmail(name: string): string {
  const clean = name.toLowerCase().replace(/ /g, ".");
  const domain = DOMAINS[Math.floor(Math.random() * DOMAINS.length)] as string;
  const suffix = Math.random() < 0.5 ? String(Math.floor(Math.random() * 99) + 1) : "";
  return `${clean}${suffix}@${domain}`;
}

/** Radio aria-labels repeat the whole question; keep only the leading value. */
export function shortValue(label: string | null | undefined, fallback: string): string {
  const head = (label ?? "").split(",")[0]?.trim() ?? "";
  return head || fallback;
}