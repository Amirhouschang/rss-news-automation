--
-- PostgreSQL database dump
--

\restrict fKV6r3hwmzEKTFFNGjcOiHnmK3OaR8fpp5kYWUgSA1QihMOz6fPFni9RDXXDMHf

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: news; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.news (
    news_id bigint NOT NULL,
    source_id bigint NOT NULL,
    run_id bigint NOT NULL,
    original_title text NOT NULL,
    original_url text NOT NULL,
    published_at timestamp with time zone,
    published_at_raw text,
    fetched_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    rss_summary_text text,
    rss_content_text text,
    article_text text,
    prepared_text text,
    text_basis text,
    summary_text text,
    summarized_at timestamp with time zone,
    processing_status text DEFAULT 'pending'::text NOT NULL,
    error_message text,
    raw_rss_entry jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT news_processing_status_check CHECK ((processing_status = ANY (ARRAY['pending'::text, 'processing'::text, 'success'::text, 'failed'::text, 'skipped'::text]))),
    CONSTRAINT news_text_basis_check CHECK ((text_basis = ANY (ARRAY['article'::text, 'rss_content'::text, 'rss_summary'::text, 'unavailable'::text])))
);


--
-- Name: news_news_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.news ALTER COLUMN news_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.news_news_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.runs (
    run_id bigint NOT NULL,
    run_type text NOT NULL,
    started_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    finished_at timestamp with time zone,
    model_name text NOT NULL,
    prompt_version text,
    generation_settings jsonb DEFAULT '{}'::jsonb NOT NULL,
    status text DEFAULT 'running'::text NOT NULL,
    new_count integer DEFAULT 0 NOT NULL,
    error_count integer DEFAULT 0 NOT NULL,
    error_message text,
    CONSTRAINT runs_check CHECK (((finished_at IS NULL) OR (finished_at >= started_at))),
    CONSTRAINT runs_error_count_check CHECK ((error_count >= 0)),
    CONSTRAINT runs_new_count_check CHECK ((new_count >= 0)),
    CONSTRAINT runs_run_type_check CHECK ((run_type = ANY (ARRAY['import'::text, 'daily'::text]))),
    CONSTRAINT runs_status_check CHECK ((status = ANY (ARRAY['running'::text, 'success'::text, 'partial'::text, 'failed'::text])))
);


--
-- Name: sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sources (
    source_id bigint NOT NULL,
    name text NOT NULL,
    country text NOT NULL,
    language text DEFAULT 'en'::text NOT NULL,
    feed_url text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: news_overview; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.news_overview AS
 SELECT n.news_id,
    s.country,
    s.name AS source,
    n.original_title,
    n.summary_text,
    n.original_url,
    n.published_at,
    n.fetched_at,
    n.text_basis,
    n.processing_status,
    r.model_name,
    n.run_id,
    n.error_message
   FROM ((public.news n
     JOIN public.sources s ON ((s.source_id = n.source_id)))
     JOIN public.runs r ON ((r.run_id = n.run_id)));


--
-- Name: runs_run_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.runs ALTER COLUMN run_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.runs_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: sources_source_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.sources ALTER COLUMN source_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.sources_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: news news_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_pkey PRIMARY KEY (news_id);


--
-- Name: news news_source_url_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_source_url_unique UNIQUE (source_id, original_url);


--
-- Name: runs runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.runs
    ADD CONSTRAINT runs_pkey PRIMARY KEY (run_id);


--
-- Name: sources sources_feed_url_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_feed_url_key UNIQUE (feed_url);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (source_id);


--
-- Name: news_fetched_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX news_fetched_at_idx ON public.news USING btree (fetched_at);


--
-- Name: news_processing_status_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX news_processing_status_idx ON public.news USING btree (processing_status);


--
-- Name: news_published_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX news_published_at_idx ON public.news USING btree (published_at);


--
-- Name: news_run_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX news_run_id_idx ON public.news USING btree (run_id);


--
-- Name: news news_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id);


--
-- Name: news news_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(source_id);


--
-- PostgreSQL database dump complete
--

\unrestrict fKV6r3hwmzEKTFFNGjcOiHnmK3OaR8fpp5kYWUgSA1QihMOz6fPFni9RDXXDMHf

