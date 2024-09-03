-- metatable for every result_view() table
local mt = {
    __len = function(this)
        return this.length
    end,
    __index = function(this, i)
        -- right away, convert to 0-relative indexing
        i -= 1
        -- can we find this index within the current slice?
        local reli = i - this.start
        if 0 <= reli and reli < #this.slice then
            -- Lua 1-relative indexing
            return this.slice[reli + 1]
        end
        -- is this index outside the overall result set?
        if not (0 <= i and i < this.length) then
            return nil
        end
        -- fetch a new slice starting at i, using provided fetch()
        local start
        this.slice, start = this.fetch(this.key, i)
        -- It's possible that caller-provided fetch() function forgot
        -- to return the adjusted start index of the new slice. In
        -- Lua, 0 tests as true, so if fetch() returned (slice, 0),
        -- we'll duly reset this.start to 0. Otherwise, assume the
        -- requested index was not adjusted: that the returned slice
        -- really does start at i.
        this.start = start or i
        -- Hopefully this slice contains the desired i.
        -- Back to 1-relative indexing.
        return this.slice[i - this.start + 1]
    end,
    -- We purposely avoid putting any array entries (int keys) into
    -- our table so that access to any int key will always call our
    -- __index() metamethod. Moreover, we want any table iteration to
    -- call __index(table, i) however many times; we do NOT want it to
    -- retrieve key, length, start, slice.
    -- So turn 'for k, v in result' into 'for k, v in ipairs(result)'.
    __iter = ipairs,
    -- This result set provides read-only access.
    -- We do not support pushing updates to individual items back to
    -- C++; for the intended use cases, that makes no sense.
    __newindex = function(this, i, value)
        error("result_view is a read-only data structure", 2)
    end
}

-- result_view(key_length, fetch) returns a table which stores only a slice
-- of a result set plus some control values, yet presents read-only virtual
-- access to the entire result set.
-- key_length: {result set key, total result set length}
-- fetch:      function(key, start) that returns (slice, adjusted start) 
local function result_view(key_length, fetch)
    return setmetatable(
        {
            key=key_length[1],
            length=key_length[2],
            -- C++ result sets use 0-based indexing, so internally we do too
            start=0,
            -- start with a dummy array with length 0
            slice={},
            fetch=fetch
        },
        -- use our special metatable
        mt
    )
end

return result_view
