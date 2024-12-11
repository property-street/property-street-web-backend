--
-- PostgreSQL database dump
--

-- Dumped from database version 15.7
-- Dumped by pg_dump version 15.7

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: asset_category_choice; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.asset_category_choice AS ENUM (
    'house',
    'hotel',
    'land',
    'estate',
    'fabricated_homes',
    'peng_house',
    'office_complex',
    'oriental_suite'
);


ALTER TYPE public.asset_category_choice OWNER TO postgres;

--
-- Name: client_type_choice; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.client_type_choice AS ENUM (
    'client',
    'agent'
);


ALTER TYPE public.client_type_choice OWNER TO postgres;

--
-- Name: email_management_reason_choice; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.email_management_reason_choice AS ENUM (
    'email_verification',
    'password_change',
    'verified'
);


ALTER TYPE public.email_management_reason_choice OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agents (
    id integer NOT NULL
);


ALTER TABLE public.agents OWNER TO postgres;

--
-- Name: agents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agents_id_seq OWNER TO postgres;

--
-- Name: agents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agents_id_seq OWNED BY public.agents.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: asset_cloud_images; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asset_cloud_images (
    id integer NOT NULL,
    asset_id integer,
    asset_feature_id integer,
    created_at timestamp with time zone,
    format character varying NOT NULL,
    bytes integer NOT NULL,
    height integer NOT NULL,
    public_id character varying NOT NULL,
    secure_url character varying NOT NULL,
    width integer NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    cloud_asset_id character varying NOT NULL
);


ALTER TABLE public.asset_cloud_images OWNER TO postgres;

--
-- Name: asset_cloud_images_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.asset_cloud_images_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.asset_cloud_images_id_seq OWNER TO postgres;

--
-- Name: asset_cloud_images_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.asset_cloud_images_id_seq OWNED BY public.asset_cloud_images.id;


--
-- Name: asset_features; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asset_features (
    id integer NOT NULL,
    title character varying NOT NULL,
    asset_id integer
);


ALTER TABLE public.asset_features OWNER TO postgres;

--
-- Name: asset_features_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.asset_features_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.asset_features_id_seq OWNER TO postgres;

--
-- Name: asset_features_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.asset_features_id_seq OWNED BY public.asset_features.id;


--
-- Name: asset_tag_association; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asset_tag_association (
    asset_id integer NOT NULL,
    tag_id integer NOT NULL
);


ALTER TABLE public.asset_tag_association OWNER TO postgres;

--
-- Name: assets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.assets (
    id integer NOT NULL,
    title character varying NOT NULL,
    country character varying NOT NULL,
    address character varying NOT NULL,
    currency character varying NOT NULL,
    status character varying NOT NULL,
    amount numeric NOT NULL,
    description text,
    has_features boolean,
    availability boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    category character varying NOT NULL,
    agent_id integer,
    cover_image_id integer,
    lease_duration character varying
);


ALTER TABLE public.assets OWNER TO postgres;

--
-- Name: assets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.assets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.assets_id_seq OWNER TO postgres;

--
-- Name: assets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.assets_id_seq OWNED BY public.assets.id;


--
-- Name: cloud_image_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cloud_image_details (
    id integer NOT NULL,
    created_at timestamp with time zone,
    format character varying NOT NULL,
    bytes integer NOT NULL,
    height integer NOT NULL,
    public_id character varying NOT NULL,
    secure_url character varying NOT NULL,
    width integer NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    cloud_asset_id character varying NOT NULL
);


ALTER TABLE public.cloud_image_details OWNER TO postgres;

--
-- Name: cloud_image_details_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.cloud_image_details_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.cloud_image_details_id_seq OWNER TO postgres;

--
-- Name: cloud_image_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.cloud_image_details_id_seq OWNED BY public.cloud_image_details.id;


--
-- Name: email_management_model; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.email_management_model (
    id character varying NOT NULL,
    email_address character varying,
    email_code character varying(255),
    email_code_time timestamp with time zone DEFAULT now(),
    email_link character varying,
    email_link_time timestamp with time zone DEFAULT now(),
    reason public.email_management_reason_choice
);


ALTER TABLE public.email_management_model OWNER TO postgres;

--
-- Name: tags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tags (
    id integer NOT NULL,
    name character varying NOT NULL
);


ALTER TABLE public.tags OWNER TO postgres;

--
-- Name: tags_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tags_id_seq OWNER TO postgres;

--
-- Name: tags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tags_id_seq OWNED BY public.tags.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying,
    username character varying,
    password_hash character varying NOT NULL,
    first_name character varying,
    last_name character varying,
    other_names character varying,
    date_of_birth date,
    country_of_origin character varying,
    account_status character varying,
    misc json,
    client_type public.client_type_choice,
    is_active boolean,
    is_admin boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    profile_avatar_id integer,
    agent_profile_id integer
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: agents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents ALTER COLUMN id SET DEFAULT nextval('public.agents_id_seq'::regclass);


--
-- Name: asset_cloud_images id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_cloud_images ALTER COLUMN id SET DEFAULT nextval('public.asset_cloud_images_id_seq'::regclass);


--
-- Name: asset_features id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_features ALTER COLUMN id SET DEFAULT nextval('public.asset_features_id_seq'::regclass);


--
-- Name: assets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets ALTER COLUMN id SET DEFAULT nextval('public.assets_id_seq'::regclass);


--
-- Name: cloud_image_details id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cloud_image_details ALTER COLUMN id SET DEFAULT nextval('public.cloud_image_details_id_seq'::regclass);


--
-- Name: tags id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tags ALTER COLUMN id SET DEFAULT nextval('public.tags_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: asset_cloud_images asset_cloud_images_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_cloud_images
    ADD CONSTRAINT asset_cloud_images_pkey PRIMARY KEY (id);


--
-- Name: asset_cloud_images asset_cloud_images_public_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_cloud_images
    ADD CONSTRAINT asset_cloud_images_public_id_key UNIQUE (public_id);


--
-- Name: asset_features asset_features_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_features
    ADD CONSTRAINT asset_features_pkey PRIMARY KEY (id);


--
-- Name: asset_tag_association asset_tag_association_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_tag_association
    ADD CONSTRAINT asset_tag_association_pkey PRIMARY KEY (asset_id, tag_id);


--
-- Name: assets assets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_pkey PRIMARY KEY (id);


--
-- Name: cloud_image_details cloud_image_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cloud_image_details
    ADD CONSTRAINT cloud_image_details_pkey PRIMARY KEY (id);


--
-- Name: cloud_image_details cloud_image_details_public_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cloud_image_details
    ADD CONSTRAINT cloud_image_details_public_id_key UNIQUE (public_id);


--
-- Name: email_management_model email_management_model_email_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.email_management_model
    ADD CONSTRAINT email_management_model_email_code_key UNIQUE (email_code);


--
-- Name: email_management_model email_management_model_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.email_management_model
    ADD CONSTRAINT email_management_model_pkey PRIMARY KEY (id);


--
-- Name: tags tags_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_name_key UNIQUE (name);


--
-- Name: tags tags_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_pkey PRIMARY KEY (id);


--
-- Name: users users_agent_profile_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_agent_profile_id_key UNIQUE (agent_profile_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_agents_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agents_id ON public.agents USING btree (id);


--
-- Name: ix_asset_cloud_images_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_asset_cloud_images_id ON public.asset_cloud_images USING btree (id);


--
-- Name: ix_asset_features_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_asset_features_id ON public.asset_features USING btree (id);


--
-- Name: ix_assets_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_assets_id ON public.assets USING btree (id);


--
-- Name: ix_cloud_image_details_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cloud_image_details_id ON public.cloud_image_details USING btree (id);


--
-- Name: ix_email_management_model_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_email_management_model_id ON public.email_management_model USING btree (id);


--
-- Name: ix_tags_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tags_id ON public.tags USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: asset_cloud_images fk_asset_cloud_images_asset_feature_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_cloud_images
    ADD CONSTRAINT fk_asset_cloud_images_asset_feature_id FOREIGN KEY (asset_feature_id) REFERENCES public.asset_features(id) ON DELETE CASCADE;


--
-- Name: asset_cloud_images fk_asset_cloud_images_asset_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_cloud_images
    ADD CONSTRAINT fk_asset_cloud_images_asset_id FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;


--
-- Name: asset_features fk_asset_features_asset_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_features
    ADD CONSTRAINT fk_asset_features_asset_id FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;


--
-- Name: asset_tag_association fk_asset_tag_association_asset_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_tag_association
    ADD CONSTRAINT fk_asset_tag_association_asset_id FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;


--
-- Name: asset_tag_association fk_asset_tag_association_tag_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_tag_association
    ADD CONSTRAINT fk_asset_tag_association_tag_id FOREIGN KEY (tag_id) REFERENCES public.tags(id) ON DELETE RESTRICT;


--
-- Name: assets fk_assets_agent_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT fk_assets_agent_id FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: assets fk_assets_cover_image_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT fk_assets_cover_image_id FOREIGN KEY (cover_image_id) REFERENCES public.cloud_image_details(id) ON DELETE SET NULL;


--
-- Name: users fk_user_profile_avatar_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_user_profile_avatar_id FOREIGN KEY (profile_avatar_id) REFERENCES public.cloud_image_details(id) ON DELETE SET NULL;


--
-- Name: users fk_users_agent_profile_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_agent_profile_id FOREIGN KEY (agent_profile_id) REFERENCES public.agents(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

