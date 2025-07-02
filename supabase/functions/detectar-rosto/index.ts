// supabase/functions/detectar-rosto/index.ts
import { serve } from 'https://deno.land/std/http/server.ts';

const API_KEY = Deno.env.get('FACE_API_KEY')!;
const API_SECRET = Deno.env.get('FACE_API_SECRET')!;

serve(async req => {
  try {
    const { image_url } = await req.json();

    if (!image_url) {
      return new Response(
        JSON.stringify({ error: 'URL da imagem não fornecida' }),
        { status: 400 },
      );
    }

    const formData = new URLSearchParams();
    formData.append('api_key', API_KEY);
    formData.append('api_secret', API_SECRET);
    formData.append('image_url', image_url);
    formData.append('return_attributes', 'gender,age,emotion');

    const res = await fetch(
      'https://api-us.faceplusplus.com/facepp/v3/detect',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      },
    );

    const json = await res.json();

    return new Response(JSON.stringify(json), {
      headers: { 'Content-Type': 'application/json' },
      status: res.status,
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { 'Content-Type': 'application/json' },
      status: 500,
    });
  }
});
