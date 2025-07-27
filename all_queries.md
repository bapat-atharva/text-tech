### Q: List all book titles under £15.

```
for $book in /books/item

where number(substring($book/price, 2)) < 15

return $book/title/text()
```

### Q: Show titles and prices of books in the 'Science Fiction' category.

```
for $book in /books/item

where $book/category = "Science Fiction"

return {$book/title/text() - $book/price/text() }
```

### Q: List all books with a rating of Five.

```
for $book in /books/item

where $book/rating = "Five"

return $book/title/text()
```

### Q: Number of books under price of 50 pounds

```
count(

for $b in /books/item

let$price := number(translate($b/price, "£", ""))

where $price < 50

return $b )
```
