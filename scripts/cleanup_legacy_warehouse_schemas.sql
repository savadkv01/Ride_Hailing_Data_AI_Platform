drop schema if exists analytics_analytics cascade;
drop schema if exists analytics_staging cascade;

-- Optional legacy default schema from earlier profiles.
do $$
begin
    if exists (
        select 1
        from information_schema.schemata
        where schema_name = 'analytics'
    ) then
        execute 'drop schema analytics cascade';
    end if;
end $$;
