import { promises as fs } from 'fs'
import path from 'path'

export type User = {
  id: string
  email: string
  firstName: string
  lastName: string
  passwordHash: string
  createdAt: string
}

const dataDir = path.join(process.cwd(), 'data')
const dataFile = process.env.USER_STORE_FILE || path.join(dataDir, 'users.json')

async function ensureFile() {
  try {
    await fs.mkdir(path.dirname(dataFile), { recursive: true })
    await fs.access(dataFile)
  } catch {
    await fs.writeFile(dataFile, JSON.stringify([]), 'utf8')
  }
}

export async function readUsers(): Promise<User[]> {
  await ensureFile()
  const raw = await fs.readFile(dataFile, 'utf8')
  try {
    const data = JSON.parse(raw) as User[]
    return Array.isArray(data) ? data : []
  } catch {
    return []
  }
}

export async function writeUsers(users: User[]) {
  await ensureFile()
  await fs.writeFile(dataFile, JSON.stringify(users, null, 2), 'utf8')
}

export async function getUserByEmail(email: string) {
  const users = await readUsers()
  return users.find((u) => u.email.toLowerCase() === email.toLowerCase()) || null
}

export async function addUser(user: User) {
  const users = await readUsers()
  users.push(user)
  await writeUsers(users)
}

