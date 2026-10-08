--
-- PostgreSQL database dump
--

\restrict J1dg9bhayUNWEDHEdoPl7nArX5G9I2wwKNZQEnpIeyYHKOxyCNqUojO9u1SqYUP

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: sources; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.sources (source_id, name, country, language, feed_url, is_active, created_at) OVERRIDING SYSTEM VALUE VALUES (1, 'DW', 'Germany', 'en', 'https://rss.dw.com/rdf/rss-en-all', true, '2026-10-07 21:00:26.448423+02');
INSERT INTO public.sources (source_id, name, country, language, feed_url, is_active, created_at) OVERRIDING SYSTEM VALUE VALUES (2, 'IRNA', 'Iran', 'en', 'https://en.irna.ir/rss', true, '2026-10-07 21:00:26.448423+02');
INSERT INTO public.sources (source_id, name, country, language, feed_url, is_active, created_at) OVERRIDING SYSTEM VALUE VALUES (4, 'TASS', 'Russia', 'en', 'https://tass.com/rss/v2.xml', true, '2026-10-07 21:00:26.448423+02');
INSERT INTO public.sources (source_id, name, country, language, feed_url, is_active, created_at) OVERRIDING SYSTEM VALUE VALUES (5, 'Ukrinform', 'Ukraine', 'en', 'https://www.ukrinform.net/rss/block-lastnews', true, '2026-10-07 21:00:26.448423+02');
INSERT INTO public.sources (source_id, name, country, language, feed_url, is_active, created_at) OVERRIDING SYSTEM VALUE VALUES (3, 'ECNS', 'China', 'en', 'https://www.ecns.cn/rss/rss.xml', false, '2026-10-07 21:00:26.448423+02');
INSERT INTO public.sources (source_id, name, country, language, feed_url, is_active, created_at) OVERRIDING SYSTEM VALUE VALUES (6, 'CGTN', 'China', 'en', 'https://www.cgtn.com/subscribe/rss/section/world.xml', true, '2026-10-07 22:13:58.12504+02');


--
-- Name: sources_source_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sources_source_id_seq', 9, true);


--
-- PostgreSQL database dump complete
--

\unrestrict J1dg9bhayUNWEDHEdoPl7nArX5G9I2wwKNZQEnpIeyYHKOxyCNqUojO9u1SqYUP

