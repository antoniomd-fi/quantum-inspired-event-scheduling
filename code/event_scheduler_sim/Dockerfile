FROM elixir:1.17.3-otp-27-alpine

WORKDIR /app

ENV MIX_ENV=dev

COPY mix.exs ./
RUN mix deps.get

COPY . .

CMD ["mix", "test"]
