/**
 * Guarda de endereco local.
 *
 * O piloto so fala com um servidor na maquina de quem executa. Esta camada e a
 * unica duena da regra, porque o cliente e o worker de demonstracao precisam da
 * mesma guarda e uma copia divergente seria um buraco de seguranca.
 */
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { DEFAULT_PILOT_ADDRESS, checkLocalAddress, resolveAddressArgument } from '../src/local-address.js'

test('o endereco padrao do piloto e o servidor local do SDK', () => {
    assert.equal(DEFAULT_PILOT_ADDRESS, '127.0.0.1:7233')
    assert.equal(checkLocalAddress(DEFAULT_PILOT_ADDRESS), null)
})

test('host local aceito em todas as formas escritas', () => {
    for (const value of ['127.0.0.1:7233', 'localhost:7233', 'localhost:7234', '::1:7233', '[::1]:7233']) {
        assert.equal(checkLocalAddress(value), null, `deveria aceitar ${value}`)
    }
})

test('endereco remoto, sem porta ou com porta fora de faixa e recusado', () => {
    const recusados = ['temporal.example.com:443', '10.0.0.5:7233', 'example.com:7233', '8.8.8.8:53', '127.0.0.1', '127.0.0.1:', '127.0.0.1:0', '127.0.0.1:70000', '127.0.0.1:abc', ':7233', 'producao.suaempresa.net:7233']

    for (const value of recusados) {
        const problem = checkLocalAddress(value)

        assert.notEqual(problem, null, `deveria recusar ${value}`)
        assert.ok(problem!.includes('localhost') || problem!.includes('porta') || problem!.includes('forma'), `a recusa de ${value} nao explica o que esperar: ${problem}`)
    }
})

test('a recusa nomeia o host recebido, sem repetir outros valores', () => {
    const problem = checkLocalAddress('nao-local.example:7233')

    assert.ok(problem !== null)
    assert.ok(problem.includes('nao-local.example'))
})

test('nenhum argumento resolve no endereco padrao', () => {
    assert.deepEqual(resolveAddressArgument([]), { ok: true, address: DEFAULT_PILOT_ADDRESS })
})

test('exatamente uma flag --address com host local e aceita', () => {
    assert.deepEqual(resolveAddressArgument(['--address', 'localhost:7234']), { ok: true, address: 'localhost:7234' })
})

test('forma reconhecida com host remoto e recusada pela guarda de host, nao pela de flags', () => {
    const resolved = resolveAddressArgument(['--address', 'nao-local.example:7233'])

    assert.equal(resolved.ok, false)
    assert.ok(!resolved.ok)
    assert.match(resolved.message, /localhost/)
})

test('qualquer outra forma de argumento e recusada sem conectar nada', () => {
    const casos = [['--address'], ['--address', '--request-id', 'req-1'], ['--request-id', 'req-1'], ['--address', 'localhost:7233', '--address', 'localhost:7234'], ['extra']]

    for (const argv of casos) {
        const resolved = resolveAddressArgument(argv)

        assert.equal(resolved.ok, false, `deveria recusar: ${argv.join(' ')}`)
        assert.ok(!resolved.ok)
        assert.match(resolved.message, /--address/)
    }
})
