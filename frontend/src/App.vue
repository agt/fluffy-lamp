<template>
  <div class="app">
    <header>
      <h1>📌 Bulletin Board</h1>
      <p class="subtitle">Share your thoughts with the world</p>
    </header>

    <main>
      <!-- Post form -->
      <section class="post-form-card">
        <h2>Post a Note</h2>
        <form @submit.prevent="submitNote">
          <div class="field">
            <input
              v-model="form.author"
              type="text"
              placeholder="Your name (optional)"
              maxlength="100"
              class="input"
            />
          </div>
          <div class="field">
            <textarea
              v-model="form.content"
              placeholder="What's on your mind?"
              maxlength="1000"
              rows="3"
              class="textarea"
              required
            ></textarea>
            <span class="char-count">{{ form.content.length }}/1000</span>
          </div>
          <button type="submit" class="btn-primary" :disabled="posting">
            {{ posting ? 'Posting…' : 'Post Note' }}
          </button>
        </form>
      </section>

      <!-- Error banner -->
      <div v-if="error" class="error-banner">{{ error }}</div>

      <!-- Loading -->
      <div v-if="loading" class="loading">Loading notes…</div>

      <!-- Notes grid -->
      <section v-else class="notes-grid">
        <div v-if="notes.length === 0" class="empty">
          No notes yet. Be the first to post!
        </div>
        <NoteCard
          v-for="note in notes"
          :key="note.id"
          :note="note"
          @react="handleReact"
          @delete="handleDelete"
        />
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import NoteCard from './NoteCard.vue'

const notes = ref([])
const loading = ref(true)
const posting = ref(false)
const error = ref(null)
const form = ref({ author: '', content: '' })

async function fetchNotes() {
  try {
    const res = await fetch('/api/notes')
    if (!res.ok) throw new Error('Failed to load notes')
    notes.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function submitNote() {
  if (!form.value.content.trim()) return
  posting.value = true
  error.value = null
  try {
    const res = await fetch('/api/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        author: form.value.author.trim() || 'Anonymous',
        content: form.value.content.trim(),
      }),
    })
    if (!res.ok) throw new Error('Failed to post note')
    const note = await res.json()
    notes.value.unshift(note)
    form.value.content = ''
    form.value.author = ''
  } catch (e) {
    error.value = e.message
  } finally {
    posting.value = false
  }
}

async function handleReact({ noteId, emoji }) {
  try {
    const res = await fetch(`/api/notes/${noteId}/reactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ emoji }),
    })
    if (!res.ok) throw new Error('Reaction failed')
    // Update local state optimistically
    const note = notes.value.find(n => n.id === noteId)
    if (note) {
      const existing = note.reactions.find(r => r.emoji === emoji)
      if (existing) {
        existing.count++
      } else {
        note.reactions.push({ emoji, count: 1 })
      }
    }
  } catch (e) {
    error.value = e.message
  }
}

async function handleDelete(noteId) {
  try {
    const res = await fetch(`/api/notes/${noteId}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Delete failed')
    notes.value = notes.value.filter(n => n.id !== noteId)
  } catch (e) {
    error.value = e.message
  }
}

onMounted(fetchNotes)
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f0f2f5;
  color: #1a1a1a;
  min-height: 100vh;
}

.app {
  max-width: 860px;
  margin: 0 auto;
  padding: 0 16px 48px;
}

header {
  text-align: center;
  padding: 36px 0 24px;
}

header h1 {
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.subtitle {
  color: #666;
  margin-top: 6px;
}

/* Form card */
.post-form-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  margin-bottom: 28px;
}

.post-form-card h2 {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 16px;
}

.field { margin-bottom: 12px; position: relative; }

.input, .textarea {
  width: 100%;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 0.95rem;
  font-family: inherit;
  transition: border-color .15s;
  background: #fafafa;
}

.input:focus, .textarea:focus {
  outline: none;
  border-color: #4f6ef7;
  background: #fff;
}

.textarea { resize: vertical; }

.char-count {
  position: absolute;
  bottom: 8px;
  right: 12px;
  font-size: 0.75rem;
  color: #aaa;
  pointer-events: none;
}

.btn-primary {
  background: #4f6ef7;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 24px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s, opacity .15s;
}

.btn-primary:hover:not(:disabled) { background: #3a59e0; }
.btn-primary:disabled { opacity: .55; cursor: not-allowed; }

.error-banner {
  background: #fff0f0;
  color: #c0392b;
  border: 1px solid #f5c6cb;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 20px;
  font-size: 0.9rem;
}

.loading, .empty {
  text-align: center;
  color: #888;
  padding: 48px 0;
  font-size: 1rem;
}

/* Grid */
.notes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
</style>
