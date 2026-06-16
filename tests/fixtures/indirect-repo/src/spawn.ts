import { spawn, execSync } from 'child_process'

export function runClaude(claudePath: string, prompt: string) {
  const args = ['-p', prompt, '--output-format', 'stream-json']
  // 真实调用：spawn 一个 claude 二进制 —— 应被标为 low 置信度信号
  const proc = spawn(claudePath, args)

  // 以下不应误报：二进制定位、node 包装进程
  execSync('where claude')
  spawn(process.execPath, ['wrapper.js'])
  return proc
}
