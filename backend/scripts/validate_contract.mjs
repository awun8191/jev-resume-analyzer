// Load the binding frontend schema without changing frontend or saving report fixtures.
import fs from 'node:fs'
import { createRequire } from 'node:module'
const require = createRequire(new URL('../../frontend/package.json', import.meta.url))
const ts = require('typescript')
const source = fs.readFileSync(new URL('../../frontend/src/api/schema.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: {
  module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
} }).outputText
const module = { exports: {} }
new Function('require', 'module', 'exports', compiled)(require, module, module.exports)
const payload = JSON.parse(fs.readFileSync(0, 'utf8'))
let failures = 0
for (const entry of payload) {
  const parsed = module.exports[entry.schema].safeParse(entry.data)
  if (!parsed.success) failures++
}
console.log(JSON.stringify({ checked: payload.length, failures }))
process.exitCode = failures ? 1 : 0
