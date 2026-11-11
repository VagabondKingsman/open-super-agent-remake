import type { Bot, Chat } from './types'

/** What a chat is called in the sidebar and in the header.
 *
 *  A group chat is its own title. A direct chat is the bot's name — two direct chats with the
 *  same bot (a scratch chat made by a script, say) would otherwise both read "Nova" with the
 *  same face and the same preview colour, and there is no way to see which one you are in.
 *  So when the chat carries a title of its own, it rides after the bot's name. A rename of the
 *  bot rewrites only the titles that still follow the old name (see bots.update), so a title
 *  someone chose stays as they chose it.
 */
export function chatLabel(chat: Pick<Chat, 'kind' | 'title' | 'bot_ids'>, bots: Pick<Bot, 'id' | 'name'>[]): string {
  if (chat.kind !== 'direct') return chat.title
  const bot = bots.find(b => b.id === chat.bot_ids[0])
  const name = bot ? bot.name : ''
  const own = (chat.title || '').trim()
  if (!name) return own
  return own && own !== name ? `${name} · ${own}` : name
}
