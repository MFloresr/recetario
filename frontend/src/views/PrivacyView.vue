<script setup lang="ts">
const CONTACTO = 'mrsitofull@gmail.com'
const ACTUALIZADO = '20 de octubre de 2026'
</script>

<template>
  <v-container class="privacy-view py-6" style="max-width: 760px">
    <v-btn variant="text" prepend-icon="mdi-arrow-left" :to="{ name: 'home' }" class="mb-2"
      >Volver</v-btn
    >
    <h1 class="text-h4 font-weight-bold mb-1">Aviso de privacidad</h1>
    <p class="text-medium-emphasis mb-6">Última actualización: {{ ACTUALIZADO }}</p>

    <section class="mb-6">
      <h2 class="text-h6 mb-2">Quién es el responsable</h2>
      <p>
        Recetario es un proyecto personal de Mario Flores, sin ánimo de lucro. Para cualquier duda
        sobre tus datos, escribe a
        <a :href="`mailto:${CONTACTO}`">{{ CONTACTO }}</a
        >.
      </p>
    </section>

    <section class="mb-6">
      <h2 class="text-h6 mb-2">Qué datos guarda</h2>
      <ul class="pl-5">
        <li>
          <strong>De tu cuenta:</strong> correo electrónico, nombre de usuario y contraseña. La
          contraseña se guarda cifrada y nadie puede leerla.
        </li>
        <li>
          <strong>Lo que usas en la app:</strong> los ingredientes de tu despensa, tu lista de la
          compra y tus recetas favoritas con tus notas.
        </li>
        <li>
          <strong>Datos técnicos:</strong> tu dirección IP se usa para limitar el número de
          registros y de peticiones, y el servidor de alojamiento guarda registros técnicos de las
          peticiones durante un tiempo limitado.
        </li>
      </ul>
    </section>

    <section class="mb-6">
      <h2 class="text-h6 mb-2">Para qué se usan</h2>
      <p>
        Solo para que la aplicación funcione: iniciar sesión, mostrarte tus datos y proponerte
        recetas. No se usan para publicidad, no se venden y no se hacen perfiles. La base legal es
        prestarte el servicio que has pedido al crear la cuenta.
      </p>
    </section>

    <section class="mb-6">
      <h2 class="text-h6 mb-2">Con qué servicios se comparten datos</h2>
      <p>La app se apoya en servicios de terceros. Algunos están fuera de la Unión Europea.</p>
      <ul class="pl-5">
        <li><strong>Vercel</strong>: aloja la web y la API.</li>
        <li><strong>Supabase</strong>: guarda la base de datos (servidores en Londres).</li>
        <li>
          <strong>TheMealDB</strong>: de donde salen las recetas. Se le consultan nombres de
          ingredientes, sin datos tuyos.
        </li>
        <li>
          <strong>MyMemory</strong> (traducción): recibe textos de recetas y las búsquedas por
          nombre que escribes, sin tu cuenta.
        </li>
        <li>
          <strong>Google Gemini</strong> (IA): recibe los nombres de tus ingredientes cuando pides
          ideas con IA, sin tu cuenta. Es un servicio gratuito y Google puede usar esos textos para
          mejorar sus productos.
        </li>
        <li>
          <strong>Wikipedia</strong>: de donde salen las fotos orientativas; se le consulta el
          nombre del plato.
        </li>
      </ul>
    </section>

    <section class="mb-6">
      <h2 class="text-h6 mb-2">Cookies y almacenamiento en tu navegador</h2>
      <p>
        No usa cookies, ni analítica, ni publicidad. Solo guarda en tu navegador lo imprescindible
        para funcionar: la sesión iniciada y tu preferencia de tema claro u oscuro. Por eso no
        necesita pedirte consentimiento de cookies.
      </p>
    </section>

    <section class="mb-6">
      <h2 class="text-h6 mb-2">Cuánto tiempo se guardan</h2>
      <p>
        Mientras tengas la cuenta. Al borrarla se eliminan tus datos de inmediato; el proveedor de
        la base de datos puede conservarlos durante un tiempo limitado en sus copias de seguridad.
      </p>
    </section>

    <section class="mb-6">
      <h2 class="text-h6 mb-2">Tus derechos</h2>
      <p>
        Puedes acceder a tus datos, rectificarlos, pedir que se supriman, oponerte a su uso,
        limitarlo o pedir una copia. Puedes
        <strong>borrar tu cuenta tú mismo</strong> en cualquier momento desde el menú de tu cuenta
        («Eliminar mi cuenta»). Para cualquier otro derecho, escribe a
        <a :href="`mailto:${CONTACTO}`">{{ CONTACTO }}</a
        >. Si crees que no se han respetado, puedes reclamar ante la Agencia Española de Protección
        de Datos (aepd.es).
      </p>
    </section>
  </v-container>
</template>
