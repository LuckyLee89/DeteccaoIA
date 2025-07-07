import { serve } from 'https://deno.land/std/http/server.ts';

serve(async req => {
  try {
    const body = await req.json();

    const process = Deno.run({
      cmd: ['python3', 'index.py'],
      stdin: 'piped',
      stdout: 'piped',
      stderr: 'piped',
    });

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    await process.stdin.write(encoder.encode(JSON.stringify(body)));
    process.stdin.close();

    const output = await process.output();
    const result = decoder.decode(output);

    const { code } = await process.status();
    process.close();

    if (code === 0) {
      return new Response(result, {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    } else {
      const error = decoder.decode(await process.stderrOutput());
      return new Response(JSON.stringify({ error }), { status: 500 });
    }
  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), { status: 500 });
  }
});
